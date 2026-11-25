"""The backend's MQTT client. Started and stopped with the FastAPI app (see app/main.py).

paho runs the network loop in its own thread and reconnects by itself if the broker goes
away. We subscribe in on_connect, so the subscriptions come back after every reconnect.
"""

import logging
import uuid

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.core import clock
from app.ingest.service import handle_reading, handle_status

log = logging.getLogger(__name__)

TOPICS = [("bins/+/readings", 1), ("bins/+/status", 1)]


class Ingestor:
    def __init__(self, make_session: sessionmaker[Session]):
        self.make_session = make_session
        # Random suffix so two backends (e.g. uvicorn --reload) don't kick each other off.
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"{settings.mqtt_user}-{uuid.uuid4().hex[:6]}",
        )
        self.client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def start(self) -> None:
        # connect_async never blocks or fails app startup. The loop keeps trying.
        self.client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT connect refused: %s", reason_code)
            return
        log.info("MQTT connected, subscribing to %s", [topic for topic, _ in TOPICS])
        client.subscribe(TOPICS)

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        log.warning("MQTT disconnected (%s), will reconnect", reason_code)

    def on_message(self, client, userdata, message):
        # One bad message must never stop the client, so log and carry on.
        try:
            with self.make_session() as session:
                if message.topic.endswith("/readings"):
                    handle_reading(session, message.topic, message.payload, clock.now())
                elif message.topic.endswith("/status"):
                    handle_status(
                        session, message.topic, message.payload, clock.now(), message.retain
                    )
        except Exception:
            log.exception("Failed to handle MQTT message on %s", message.topic)

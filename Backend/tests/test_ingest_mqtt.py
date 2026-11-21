"""BE-02 end to end: publish on the real broker, the backend's client stores it.

Needs the broker and Postgres (docker compose up). Skipped if the broker is not reachable.
"""

import json
import os
import socket
import time
import uuid
from datetime import UTC, datetime

import paho.mqtt.client as mqtt
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.ingest.mqtt_client import Ingestor
from app.models import Bin, Reading, RejectedReading

pytestmark = pytest.mark.integration

POINT = "SRID=4326;POINT(-1.5733 6.6747)"


@pytest.fixture(scope="module", autouse=True)
def broker_available():
    try:
        socket.create_connection((settings.mqtt_host, settings.mqtt_port), timeout=2).close()
    except OSError:
        message = f"MQTT broker not reachable at {settings.mqtt_host}:{settings.mqtt_port}"
        if os.environ.get("MQTT_TESTS_REQUIRED") == "1":
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture
def ingestor(migrated_engine):
    with Session(migrated_engine) as session:
        session.add(Bin(id="BIN-001", name="Test bin", location=POINT, depth_cm=100, volume_l=240))
        session.commit()
    running = Ingestor(sessionmaker(migrated_engine))
    connected = []
    running.client.on_subscribe = lambda *args: connected.append(True)
    running.start()
    deadline = time.monotonic() + 5
    while not connected and time.monotonic() < deadline:
        time.sleep(0.05)
    assert connected, "backend client did not connect and subscribe"
    yield running
    running.stop()


def publish(topic: str, payload: bytes) -> None:
    """Publish as the simulator, which is allowed to write for any bin."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test-{uuid.uuid4().hex[:8]}")
    client.username_pw_set(settings.mqtt_sim_user, settings.mqtt_sim_password)
    client.connect(settings.mqtt_host, settings.mqtt_port)
    client.loop_start()
    client.publish(topic, payload, qos=1).wait_for_publish(timeout=5)
    client.disconnect()
    client.loop_stop()


def wait_for(engine, query, timeout_s: float):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with Session(engine) as session:
            row = session.scalars(query).first()
            if row is not None:
                return row
        time.sleep(0.05)
    return None


def reading(**changes) -> bytes:
    data = {
        "bin_id": "BIN-001",
        "fill": 72,
        "distance_cm": 28.4,
        "battery": 95,
        "rssi": -61,
        "seq": 1,
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fw": "1.0.0",
    }
    data.update(changes)
    return json.dumps(data).encode()


def test_valid_reading_is_stored_within_1_second(ingestor, migrated_engine):
    publish("bins/BIN-001/readings", reading())
    sent = time.monotonic()
    saved = wait_for(migrated_engine, select(Reading), timeout_s=1)
    assert saved is not None, "reading was not stored within 1 s"
    assert saved.fill == 72
    print(f"stored after {time.monotonic() - sent:.2f} s")


def test_bad_reading_lands_in_rejected_readings(ingestor, migrated_engine):
    publish("bins/BIN-001/readings", reading(fill=101))
    rejected = wait_for(migrated_engine, select(RejectedReading), timeout_s=2)
    assert rejected is not None
    assert rejected.reason == "fill_out_of_range"

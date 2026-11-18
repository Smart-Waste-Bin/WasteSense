"""BE-05: hand events to connected WebSocket clients (contract section 7, "Who gets what").

events.emit() is called from many threads: the MQTT client, the 60 s status job and API
requests. Each client lives on the server's event loop, so events are handed over with
call_soon_threadsafe into the client's own queue. ws.py sends from that queue.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.api.schemas import utc_z
from app.core import clock
from app.models.enums import UserRole

log = logging.getLogger(__name__)

STAFF = {UserRole.ADMIN.value, UserRole.SUPERVISOR.value}


@dataclass(eq=False)
class Client:
    user_id: str
    role: str
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


def should_receive(client: Client, event_type: str, data: dict[str, Any]) -> bool:
    # A notification goes only to the user it is for, whatever their role.
    if event_type == "notification":
        return str(data.get("user_id")) == client.user_id
    # Admin and supervisor get every other event.
    if client.role in STAFF:
        return True
    # A collector gets only their own routes.
    if event_type == "route_updated":
        return str(data.get("collector_id")) == client.user_id
    return False


def message_for(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    if event_type == "notification":
        # user_id only says who it is for. The contract's notification has no user_id.
        data = {key: value for key, value in data.items() if key != "user_id"}
    return {"type": event_type, "data": data, "ts": utc_z(clock.now())}


class Hub:
    def __init__(self) -> None:
        self._clients: set[Client] = set()
        self._lock = threading.Lock()

    def add(self, client: Client) -> None:
        with self._lock:
            self._clients.add(client)

    def remove(self, client: Client) -> None:
        with self._lock:
            self._clients.discard(client)

    def count(self) -> int:
        with self._lock:
            return len(self._clients)

    def on_event(self, event_type: str, data: dict[str, Any]) -> None:
        """The events listener. Safe to call from any thread."""
        with self._lock:
            clients = list(self._clients)
        message = None
        for client in clients:
            if not should_receive(client, event_type, data):
                continue
            message = message or message_for(event_type, data)
            try:
                client.loop.call_soon_threadsafe(client.queue.put_nowait, message)
            except RuntimeError:
                # The client's loop is already closed (server stopping). Nothing to send to.
                self.remove(client)


hub = Hub()

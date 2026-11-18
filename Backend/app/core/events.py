"""A tiny in-process event bus.

The backend emits events (e.g. bin_updated) here. The WebSocket (BE-05) listens and sends
them to clients. Tests can listen too. Listeners get (event_type, data).
"""

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

Listener = Callable[[str, dict[str, Any]], None]

_listeners: list[Listener] = []


def add_listener(listener: Listener) -> None:
    _listeners.append(listener)


def remove_listener(listener: Listener) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def emit(event_type: str, data: dict[str, Any]) -> None:
    for listener in list(_listeners):
        # A broken listener must never break ingestion.
        try:
            listener(event_type, data)
        except Exception:
            log.exception("Event listener failed for %s", event_type)

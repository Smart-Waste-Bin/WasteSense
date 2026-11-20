"""The current time, in one place so tests can move it (monkeypatch app.core.clock.now)."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)

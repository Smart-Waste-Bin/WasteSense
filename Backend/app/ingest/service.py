"""Stores readings and status messages that came in over MQTT."""

import json
import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.validation import bin_id_from_topic, check_reading, is_late
from app.models import Bin, Reading, RejectedReading, Setting
from app.models.enums import BinStatus

log = logging.getLogger(__name__)

DEFAULT_REPORTING_INTERVAL_S = 300


def get_live_bin(session: Session, bin_id: str) -> Bin | None:
    """The bin, or None if it doesn't exist or is deleted."""
    found = session.get(Bin, bin_id)
    if found is None or found.deleted_at is not None:
        return None
    return found


def reporting_interval_s(session: Session) -> int:
    row = session.get(Setting, "reporting_interval_s")
    return int(row.value) if row is not None else DEFAULT_REPORTING_INTERVAL_S


def handle_reading(session: Session, topic: str, payload: bytes, now: datetime) -> str:
    """Store one reading. Returns what happened: "stored", "duplicate" or the reject reason."""
    result = check_reading(
        topic, payload, lambda bin_id: get_live_bin(session, bin_id) is not None, now
    )

    if result.reason is not None:
        session.add(
            RejectedReading(topic=topic, raw=result.raw, reason=result.reason, received_at=now)
        )
        session.commit()
        log.info("Rejected reading on %s: %s", topic, result.reason)
        return result.reason

    reading = result.reading
    taken_at = result.taken_at
    assert reading is not None and taken_at is not None

    # QoS 1 can deliver the same message twice. Same (bin_id, seq) is not saved again,
    # but goes in rejected_readings as "duplicate" so it can be counted (contract section 4).
    already_saved = session.scalar(
        select(Reading.id).where(Reading.bin_id == reading.bin_id, Reading.seq == reading.seq)
    )
    if already_saved is not None:
        session.add(
            RejectedReading(topic=topic, raw=result.raw, reason="duplicate", received_at=now)
        )
        session.commit()
        return "duplicate"

    newer_saved = session.scalar(
        select(Reading.id).where(Reading.bin_id == reading.bin_id, Reading.device_ts > taken_at)
    )

    session.add(
        Reading(
            bin_id=reading.bin_id,
            fill=int(reading.fill),
            distance_cm=reading.distance_cm,
            battery=reading.battery,
            rssi=reading.rssi,
            seq=reading.seq,
            device_ts=taken_at,
            received_at=now,
            is_late=is_late(taken_at, now, reporting_interval_s(session)),
        )
    )

    the_bin = get_live_bin(session, reading.bin_id)
    assert the_bin is not None
    the_bin.last_seen_at = now
    # A late reading goes into history but must not overwrite a newer fill.
    if newer_saved is None:
        the_bin.last_fill = Decimal(int(reading.fill))
        the_bin.last_battery = None if reading.battery is None else Decimal(reading.battery)

    session.commit()
    return "stored"


def handle_status(
    session: Session, topic: str, payload: bytes, now: datetime, retained: bool = False
) -> str:
    """Handle bins/{id}/status. Returns what happened, for logs and tests."""
    bin_id = bin_id_from_topic(topic)
    the_bin = get_live_bin(session, bin_id) if bin_id else None
    if the_bin is None:
        log.info("Status for unknown bin on %s, ignored", topic)
        return "unknown_bin"

    try:
        data = json.loads(payload.decode("utf-8", errors="replace"))
        state = data["state"]
    except (ValueError, TypeError, KeyError):
        log.info("Bad status message on %s, ignored", topic)
        return "malformed"

    if state == "online":
        # A retained message is old news from before we connected, so it says nothing about now.
        if not retained:
            the_bin.last_seen_at = now
    elif state == "offline":
        # Maintenance wins over every other status.
        if not the_bin.maintenance:
            the_bin.status = BinStatus.OFFLINE.value
    else:
        log.info("Unknown state %r on %s, ignored", state, topic)
        return "malformed"

    session.commit()
    return state

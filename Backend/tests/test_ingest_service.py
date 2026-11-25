"""BE-02: what gets saved for each reading and status message. Needs Postgres."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingest.service import handle_reading, handle_status
from app.models import Bin, Reading, RejectedReading, Setting

EXAMPLES = Path(__file__).resolve().parents[2] / "Docs" / "contract" / "examples"
POINT = "SRID=4326;POINT(-1.5733 6.6747)"
NOW = datetime(2026, 11, 7, 8, 31, tzinfo=UTC)
TOPIC = "bins/BIN-001/readings"


def payload(**changes) -> bytes:
    reading = json.loads((EXAMPLES / "mqtt/reading.json").read_text(encoding="utf-8"))
    reading.update(changes)
    return json.dumps(reading).encode()


@pytest.fixture
def session(migrated_engine):
    with Session(migrated_engine) as session:
        session.add(Bin(id="BIN-001", name="Test bin", location=POINT, depth_cm=100, volume_l=240))
        session.add(
            Bin(
                id="BIN-002",
                name="Deleted bin",
                location=POINT,
                depth_cm=100,
                volume_l=240,
                deleted_at=NOW,
            )
        )
        session.commit()
        yield session


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_valid_reading_is_stored_and_updates_the_bin(session):
    assert handle_reading(session, TOPIC, payload(), NOW) == "stored"

    saved = session.scalars(select(Reading)).one()
    assert (saved.fill, saved.seq, saved.battery, saved.rssi) == (72, 1042, 95, -61)
    assert saved.device_ts == datetime(2026, 11, 7, 8, 30, tzinfo=UTC)
    assert saved.is_late is False

    the_bin = session.get(Bin, "BIN-001")
    assert (the_bin.last_fill, the_bin.last_battery, the_bin.last_seen_at) == (72, 95, NOW)


@pytest.mark.parametrize(
    ("topic", "data", "reason"),
    [
        ("bins/BIN-999/readings", payload(bin_id="BIN-999"), "unknown_bin"),
        # A deleted bin counts as unknown.
        ("bins/BIN-002/readings", payload(bin_id="BIN-002"), "unknown_bin"),
        (TOPIC, payload(fill=101), "fill_out_of_range"),
        (TOPIC, payload(ts="07/11/2026 08:30"), "bad_timestamp"),
        (TOPIC, b'{"bin_id":"BIN-001",', "malformed"),
    ],
)
def test_invalid_reading_lands_in_rejected_readings(session, topic, data, reason):
    assert handle_reading(session, topic, data, NOW) == reason

    rejected = session.scalars(select(RejectedReading)).one()
    assert (rejected.reason, rejected.topic, rejected.received_at) == (reason, topic, NOW)
    assert count(session, Reading) == 0


def test_not_json_is_saved_as_a_json_string(session):
    handle_reading(session, TOPIC, b"not json", NOW)
    assert session.scalars(select(RejectedReading.raw)).one() == "not json"


def test_duplicate_is_not_stored_twice_but_is_counted(session):
    assert handle_reading(session, TOPIC, payload(), NOW) == "stored"
    assert handle_reading(session, TOPIC, payload(), NOW) == "duplicate"
    assert count(session, Reading) == 1
    rejected = session.scalars(select(RejectedReading)).one()
    assert (rejected.reason, rejected.raw["seq"]) == ("duplicate", 1042)


def test_late_reading_is_flagged_and_does_not_overwrite_a_newer_fill(session):
    handle_reading(session, TOPIC, payload(seq=1042, fill=72), NOW)
    late = payload(seq=1043, fill=40, ts="2026-11-07T08:15:00Z")  # 16 min old
    assert handle_reading(session, TOPIC, late, NOW) == "stored"

    saved = session.scalars(select(Reading).where(Reading.seq == 1043)).one()
    assert saved.is_late is True
    assert session.get(Bin, "BIN-001").last_fill == 72


def test_late_rule_reads_the_interval_from_settings(session):
    session.add(Setting(key="reporting_interval_s", value=60))
    session.commit()
    four_minutes_old = payload(ts=(NOW - timedelta(minutes=4)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    handle_reading(session, TOPIC, four_minutes_old, NOW)
    assert session.scalars(select(Reading.is_late)).one() is True  # 4 min > 2 x 60 s


def test_online_status_updates_last_seen_at(session):
    assert handle_status(session, "bins/BIN-001/status", b'{"state":"online","fw":"1.0.0"}', NOW)
    assert session.get(Bin, "BIN-001").last_seen_at == NOW


def test_retained_online_status_does_not_change_last_seen_at(session):
    handle_status(session, "bins/BIN-001/status", b'{"state":"online"}', NOW, retained=True)
    assert session.get(Bin, "BIN-001").last_seen_at is None


def test_offline_status_marks_the_bin_offline(session):
    assert handle_status(session, "bins/BIN-001/status", b'{"state":"offline"}', NOW) == "offline"
    assert session.get(Bin, "BIN-001").status == "offline"


def test_offline_status_leaves_a_bin_in_maintenance_alone(session):
    session.get(Bin, "BIN-001").maintenance = True
    session.get(Bin, "BIN-001").status = "maintenance"
    session.commit()
    handle_status(session, "bins/BIN-001/status", b'{"state":"offline"}', NOW)
    assert session.get(Bin, "BIN-001").status == "maintenance"


@pytest.mark.parametrize(
    ("topic", "data", "result"),
    [
        ("bins/BIN-999/status", b'{"state":"offline"}', "unknown_bin"),
        ("bins/BIN-001/status", b"not json", "malformed"),
        ("bins/BIN-001/status", b'{"state":"sleeping"}', "malformed"),
    ],
)
def test_bad_status_messages_are_ignored(session, topic, data, result):
    assert handle_status(session, topic, data, NOW) == result
    assert session.get(Bin, "BIN-001").status == "normal"

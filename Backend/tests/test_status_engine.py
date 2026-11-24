"""BE-03: bin status engine."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core import events
from app.ingest.service import handle_reading, handle_status
from app.models import Bin, Setting
from app.models.enums import BinStatus
from app.status.engine import StatusSettings, compute_status, mark_offline_bins
from app.status.scheduler import CHECK_EVERY_S, start_status_job

DOCS = Path(__file__).resolve().parents[2] / "Docs" / "contract" / "examples"
NOW = datetime(2026, 11, 7, 8, 31, tzinfo=UTC)
DEFAULT = StatusSettings(due_threshold=70, urgent_threshold=90, offline_timeout_min=15)
POINT = "SRID=4326;POINT(-1.5733 6.6747)"


def status(fill, last_seen_at=NOW, maintenance=False, settings=DEFAULT, now=NOW):
    return compute_status(fill, last_seen_at, maintenance, settings, now)


# --- The rules and their boundaries (pure function, no database) ---


@pytest.mark.parametrize(
    ("fill", "expected"),
    [
        (0, BinStatus.NORMAL),
        (49, BinStatus.NORMAL),
        (50, BinStatus.FILLING),
        (69, BinStatus.FILLING),
        (70, BinStatus.DUE),
        (89, BinStatus.DUE),
        (90, BinStatus.URGENT),
        (100, BinStatus.URGENT),
    ],
)
def test_fill_rules_and_boundaries(fill, expected):
    assert status(fill) == expected


def test_maintenance_comes_first():
    assert status(100, last_seen_at=None, maintenance=True) == BinStatus.MAINTENANCE


def test_offline_comes_before_fill():
    assert status(95, last_seen_at=NOW - timedelta(hours=1)) == BinStatus.OFFLINE


def test_offline_boundary_uses_offline_timeout_min():
    assert status(10, last_seen_at=NOW - timedelta(minutes=15)) == BinStatus.NORMAL
    assert status(10, last_seen_at=NOW - timedelta(minutes=15, seconds=1)) == BinStatus.OFFLINE


def test_bin_that_never_reported_is_offline():
    assert status(None, last_seen_at=None) == BinStatus.OFFLINE


def test_thresholds_come_from_settings():
    custom = StatusSettings(due_threshold=60, urgent_threshold=80, offline_timeout_min=15)
    assert status(60, settings=custom) == BinStatus.DUE
    assert status(80, settings=custom) == BinStatus.URGENT


# --- With the database ---


@pytest.fixture
def session(migrated_engine):
    with Session(migrated_engine) as session:
        session.add(Bin(id="BIN-001", name="Test bin", location=POINT, depth_cm=100, volume_l=240))
        session.commit()
        yield session


@pytest.fixture
def emitted():
    got = []

    def listener(event_type, data):
        got.append((event_type, data))

    events.add_listener(listener)
    yield got
    events.remove_listener(listener)


def reading(seq: int, fill: int, ts: datetime) -> bytes:
    data = json.loads((DOCS / "mqtt/reading.json").read_text(encoding="utf-8"))
    data.update(seq=seq, fill=fill, ts=ts.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return json.dumps(data).encode()


def test_status_is_updated_after_every_reading(session, emitted):
    handle_reading(session, "bins/BIN-001/readings", reading(1, 72, NOW), NOW)
    assert session.get(Bin, "BIN-001").status == "due"

    handle_reading(session, "bins/BIN-001/readings", reading(2, 91, NOW), NOW)
    assert session.get(Bin, "BIN-001").status == "urgent"

    assert [data["status"] for _, data in emitted] == ["due", "urgent"]


def test_bin_updated_event_matches_the_contract(session, emitted):
    handle_reading(session, "bins/BIN-001/readings", reading(1, 72, NOW), NOW)
    example = json.loads((DOCS / "ws/bin_updated.json").read_text(encoding="utf-8"))

    event_type, data = emitted[0]
    assert event_type == "bin_updated"
    assert set(data) == set(example["data"])
    assert data == {
        "id": "BIN-001",
        "status": "due",
        "last_fill": 72,
        "last_battery": 95,
        "last_seen_at": "2026-11-07T08:31:00Z",
    }


def test_bin_threshold_overrides_the_global_setting(session):
    session.get(Bin, "BIN-001").due_threshold = 60
    session.commit()
    handle_reading(session, "bins/BIN-001/readings", reading(1, 65, NOW), NOW)
    assert session.get(Bin, "BIN-001").status == "due"


def test_global_settings_are_read_from_the_settings_table(session):
    session.add(Setting(key="urgent_threshold", value=80))
    session.commit()
    handle_reading(session, "bins/BIN-001/readings", reading(1, 85, NOW), NOW)
    assert session.get(Bin, "BIN-001").status == "urgent"


def test_bin_goes_offline_within_1_minute_of_the_third_missed_interval(session, emitted):
    # Last reading at NOW. Reports every 5 min, so the third missed one is at NOW + 15 min.
    handle_reading(session, "bins/BIN-001/readings", reading(1, 30, NOW), NOW)
    emitted.clear()

    third_missed = NOW + timedelta(minutes=15)
    assert mark_offline_bins(session, third_missed) == []
    # The job runs every 60 s, so its next run is at most 60 s after the third missed interval.
    assert CHECK_EVERY_S == 60
    assert mark_offline_bins(session, third_missed + timedelta(seconds=CHECK_EVERY_S)) == [
        "BIN-001"
    ]
    assert session.get(Bin, "BIN-001").status == "offline"
    assert emitted[0][1]["status"] == "offline"


def test_offline_job_skips_maintenance_and_deleted_bins(session):
    the_bin = session.get(Bin, "BIN-001")
    the_bin.maintenance = True
    the_bin.status = "maintenance"
    session.add(
        Bin(
            id="BIN-002",
            name="Deleted",
            location=POINT,
            depth_cm=100,
            volume_l=240,
            deleted_at=NOW,
        )
    )
    session.commit()
    assert mark_offline_bins(session, NOW + timedelta(days=1)) == []


def test_offline_job_does_not_undo_a_last_will_offline(session):
    handle_reading(session, "bins/BIN-001/readings", reading(1, 30, NOW), NOW)
    handle_status(session, "bins/BIN-001/status", b'{"state":"offline"}', NOW)
    mark_offline_bins(session, NOW + timedelta(minutes=1))
    assert session.get(Bin, "BIN-001").status == "offline"


def test_bin_comes_back_from_offline_on_the_next_reading(session):
    handle_reading(session, "bins/BIN-001/readings", reading(1, 30, NOW), NOW)
    later = NOW + timedelta(hours=1)
    mark_offline_bins(session, later)
    assert session.get(Bin, "BIN-001").status == "offline"

    handle_reading(session, "bins/BIN-001/readings", reading(2, 75, later), later)
    assert session.get(Bin, "BIN-001").status == "due"


def test_scheduler_runs_the_offline_check_every_60_seconds():
    scheduler = start_status_job()
    try:
        job = scheduler.get_job("offline_check")
        assert job.trigger.interval == timedelta(seconds=60)
    finally:
        scheduler.shutdown(wait=False)

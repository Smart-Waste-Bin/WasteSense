from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Alert, Bin, Reading

POINT = "SRID=4326;POINT(-1.5733 6.6747)"


def add_bin(session: Session, bin_id: str = "BIN-001") -> None:
    session.add(Bin(id=bin_id, name="Test bin", location=POINT, depth_cm=100, volume_l=240))
    session.flush()


def reading(seq: int, fill: float = 50) -> Reading:
    return Reading(
        bin_id="BIN-001", fill=fill, distance_cm=50, seq=seq, device_ts=datetime.now(UTC)
    )


def test_duplicate_bin_id_and_seq_fails(migrated_engine):
    with Session(migrated_engine) as session:
        add_bin(session)
        session.add(reading(seq=1))
        session.flush()
        session.add(reading(seq=1))
        with pytest.raises(IntegrityError, match="uq_readings_bin_id_seq"):
            session.flush()


def test_fill_over_100_fails(migrated_engine):
    with Session(migrated_engine) as session:
        add_bin(session)
        session.add(reading(seq=1, fill=101))
        with pytest.raises(IntegrityError, match="ck_readings_fill_range"):
            session.flush()


def test_bad_bin_id_fails(migrated_engine):
    with Session(migrated_engine) as session:
        with pytest.raises(IntegrityError, match="ck_bins_id_format"):
            add_bin(session, bin_id="bin1")


def test_second_open_alert_of_same_type_fails(migrated_engine):
    with Session(migrated_engine) as session:
        add_bin(session)
        session.add(Alert(bin_id="BIN-001", type="urgent"))
        session.flush()
        session.add(Alert(bin_id="BIN-001", type="urgent"))
        with pytest.raises(IntegrityError, match="uq_alerts_bin_id_type_active"):
            session.flush()


def test_new_alert_allowed_after_old_one_is_resolved(migrated_engine):
    with Session(migrated_engine) as session:
        add_bin(session)
        session.add(Alert(bin_id="BIN-001", type="urgent", state="resolved"))
        session.add(Alert(bin_id="BIN-001", type="urgent"))
        session.flush()

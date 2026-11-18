# ruff: noqa: F811  (pytest fixtures imported from test_auth are used as arguments)
"""BE-07: data quality (ticket SB-19, contract v1.5)."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.ingest.service import handle_reading
from app.models import Bin, Reading, RejectedReading, Setting
from app.models.enums import UserRole
from simulator.engine import Simulation
from simulator.scenario import Scenario, Window
from tests.test_auth import START, bearer, client, fake_clock, login_as, sessions  # noqa: F401

DOCS = Path(__file__).resolve().parents[2] / "Docs" / "contract" / "examples"
TOPIC = "bins/BIN-001/readings"


def z(when):
    return when.isoformat().replace("+00:00", "Z")


@pytest.fixture
def admin(client):
    return bearer(login_as(client, UserRole.ADMIN)["access_token"])


@pytest.fixture
def bin_001(sessions):
    with sessions() as session:
        for bin_id in ("BIN-001", "BIN-002"):
            session.add(
                Bin(
                    id=bin_id,
                    name=f"Bin {bin_id}",
                    location="SRID=4326;POINT(-1.5733 6.6747)",
                    depth_cm=100,
                    volume_l=240,
                    created_at=START - timedelta(days=30),
                )
            )
        session.commit()


def add_reading(sessions, seq, taken, late=False, bin_id="BIN-001"):
    with sessions() as session:
        session.add(
            Reading(
                bin_id=bin_id,
                fill=50,
                distance_cm=50,
                battery=90,
                rssi=-60,
                seq=seq,
                device_ts=taken,
                received_at=taken,
                is_late=late,
            )
        )
        session.commit()


def add_reject(sessions, reason, received, topic=TOPIC, raw=None):
    with sessions() as session:
        session.add(
            RejectedReading(
                topic=topic, raw=raw or {"bin_id": "BIN-001"}, reason=reason, received_at=received
            )
        )
        session.commit()


def get_quality(client, admin, start, end, bin_id="BIN-001"):
    response = client.get(
        f"/api/bins/{bin_id}/quality", params={"from": z(start), "to": z(end)}, headers=admin
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- Acceptance: a 30-minute outage, a replayed message, the right numbers for a range ---


def test_after_a_30_minute_outage_late_matches_the_buffered_readings(
    client, admin, sessions, bin_001, fake_clock
):
    """The simulator's outage, delivered in real time (speed 1) through the real ingest code."""
    rows = [{"id": "BIN-001", "name": "KNUST", "depth_cm": "100"}]
    start = START - timedelta(hours=1)
    outage = Window(bin="BIN-001", start=10, minutes=30)
    sim = Simulation(rows, Scenario(fixed_seed=1, outages=[outage]), start)

    buffered_too_old = 0
    with sessions() as session:
        for step in range(12):  # minutes 0 to 55
            taken = start + timedelta(minutes=5 * step)
            arrived = taken + timedelta(seconds=1)
            for message in sim.step(taken, z(taken)):
                if not message.topic.endswith("/readings"):
                    continue
                ts = message.payload["ts"]
                if arrived - fake_parse(ts) > timedelta(minutes=10):
                    buffered_too_old += 1
                payload = json.dumps(message.payload).encode()
                assert handle_reading(session, message.topic, payload, arrived) == "stored"

    result = get_quality(client, admin, start, START)
    # Readings taken at minutes 10-35 were kept and sent at minute 40. Those more than
    # 2 x 300 s old when they arrived (minutes 10-30) are late; minute 35 is not.
    assert buffered_too_old == 5
    assert result["late"] == buffered_too_old
    assert result["received"] == 12  # nothing lost, only delayed
    assert result["missing"] == 0


def fake_parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_a_replayed_message_is_a_duplicate_not_stored_twice(
    client, admin, sessions, bin_001, fake_clock
):
    payload = (DOCS / "mqtt/reading.json").read_bytes()  # BIN-001, seq 1042, 08:30
    arrived = START + timedelta(minutes=31)
    with sessions() as session:
        assert handle_reading(session, TOPIC, payload, arrived) == "stored"
        assert handle_reading(session, TOPIC, payload, arrived) == "duplicate"
    fake_clock.move(minutes=40)  # less than the 60-minute token life

    result = get_quality(client, admin, START, START + timedelta(minutes=40))
    assert result["received"] == 1
    assert result["duplicates"] == 1
    assert result["rejected"] == 0  # a duplicate is not a rejection


def test_the_numbers_for_a_chosen_range(client, admin, sessions, bin_001, fake_clock):
    hour = START - timedelta(hours=1)  # 07:00-08:00 = 12 expected at 300 s
    for i in range(10):
        add_reading(sessions, i + 1, hour + timedelta(minutes=5 * i), late=i in (2, 3))
    add_reading(sessions, 99, hour - timedelta(minutes=5))  # before the range
    add_reading(sessions, 100, START)  # 08:00 = the end, not included
    add_reading(sessions, 1, hour, bin_id="BIN-002")  # another bin
    add_reject(sessions, "duplicate", hour + timedelta(minutes=1))
    add_reject(sessions, "fill_out_of_range", hour + timedelta(minutes=2))
    add_reject(sessions, "fill_out_of_range", hour + timedelta(minutes=3))
    add_reject(sessions, "malformed", hour + timedelta(minutes=4), raw="not json")
    add_reject(sessions, "bad_timestamp", hour - timedelta(minutes=1))  # before the range
    add_reject(sessions, "unknown_bin", hour + timedelta(minutes=5), topic="bins/BIN-002/readings")

    assert get_quality(client, admin, hour, START) == {
        "bin_id": "BIN-001",
        "from": "2026-11-07T07:00:00Z",
        "to": "2026-11-07T08:00:00Z",
        "interval_s": 300,
        "received": 10,
        "expected": 12,
        "missing": 2,
        "duplicates": 1,
        "late": 2,
        "rejected": 3,
        "rejected_by_reason": {"fill_out_of_range": 2, "malformed": 1},
    }


# --- Details ---


def test_missing_is_never_below_zero_for_a_bin_that_sends_on_change(
    client, admin, sessions, bin_001, fake_clock
):
    hour = START - timedelta(hours=1)
    for i in range(40):  # sends on change: many more than 12 in an hour (contract v1.4)
        add_reading(sessions, i + 1, hour + timedelta(seconds=90 * i))
    result = get_quality(client, admin, hour, START)
    assert (result["received"], result["expected"], result["missing"]) == (40, 12, 0)


def test_expected_counts_only_from_when_the_bin_was_added(
    client, admin, sessions, bin_001, fake_clock
):
    with sessions() as session:
        session.get(Bin, "BIN-001").created_at = START - timedelta(minutes=30)
        session.commit()
    result = get_quality(client, admin, START - timedelta(hours=2), START)
    assert result["expected"] == 6


def test_the_range_stops_at_now(client, admin, sessions, bin_001, fake_clock):
    result = get_quality(client, admin, START - timedelta(hours=1), START + timedelta(days=1))
    assert result["to"] == "2026-11-07T08:00:00Z"
    assert result["expected"] == 12


def test_default_range_is_the_last_24_hours(client, admin, bin_001, fake_clock):
    result = client.get("/api/bins/BIN-001/quality", headers=admin).json()
    assert (result["from"], result["to"]) == ("2026-11-06T08:00:00Z", "2026-11-07T08:00:00Z")
    assert result["expected"] == 288


def test_expected_follows_the_reporting_interval_setting(
    client, admin, sessions, bin_001, fake_clock
):
    with sessions() as session:
        session.add(Setting(key="reporting_interval_s", value=60))
        session.commit()
    result = get_quality(client, admin, START - timedelta(hours=1), START)
    assert (result["interval_s"], result["expected"]) == (60, 60)


def test_quality_bad_requests(client, admin, sessions, bin_001):
    collector = bearer(login_as(client, UserRole.COLLECTOR)["access_token"])
    assert client.get("/api/bins/BIN-001/quality", headers=collector).status_code == 403
    assert client.get("/api/bins/BIN-404/quality", headers=admin).status_code == 404
    backwards = {"from": z(START), "to": z(START - timedelta(hours=1))}
    assert (
        client.get("/api/bins/BIN-001/quality", params=backwards, headers=admin).status_code == 422
    )
    assert client.get("/api/bins/BIN-001/quality").status_code == 401


# --- Rejected list (the "Rejected: reason" tags) ---


def test_rejected_list_newest_first_with_reason_and_raw(
    client, admin, sessions, bin_001, fake_clock
):
    hour = START - timedelta(hours=1)
    add_reject(
        sessions,
        "fill_out_of_range",
        hour + timedelta(minutes=1),
        raw={"bin_id": "BIN-001", "fill": 120},
    )
    add_reject(sessions, "malformed", hour + timedelta(minutes=2), raw="{not json")
    add_reject(sessions, "duplicate", hour + timedelta(minutes=3))
    add_reject(sessions, "unknown_bin", hour, topic="bins/BIN-002/readings")

    response = client.get(
        "/api/bins/BIN-001/rejected", params={"from": z(hour), "to": z(START)}, headers=admin
    )
    body = response.json()
    assert body["total"] == 3
    assert [item["reason"] for item in body["items"]] == [
        "duplicate",
        "malformed",
        "fill_out_of_range",
    ]
    assert body["items"][1]["raw"] == "{not json"
    assert body["items"][2]["raw"] == {"bin_id": "BIN-001", "fill": 120}
    assert body["items"][2]["received_at"] == "2026-11-07T07:01:00Z"

    only = client.get(
        "/api/bins/BIN-001/rejected", params={"reason": "malformed", "size": 1}, headers=admin
    ).json()
    assert only["total"] == 1 and len(only["items"]) == 1


def test_rejected_list_paging_and_roles(client, admin, sessions, bin_001, fake_clock):
    for i in range(5):
        add_reject(sessions, "fill_out_of_range", START - timedelta(minutes=10 + i))
    page = client.get("/api/bins/BIN-001/rejected?page=2&size=2", headers=admin).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    collector = bearer(login_as(client, UserRole.COLLECTOR)["access_token"])
    assert client.get("/api/bins/BIN-001/rejected", headers=collector).status_code == 403
    assert client.get("/api/bins/BIN-404/rejected", headers=admin).status_code == 404


def test_docs_have_the_new_endpoints_with_examples(client):
    spec = client.get("/openapi.json").json()
    assert "get" in spec["paths"]["/api/bins/{bin_id}/quality"]
    assert "get" in spec["paths"]["/api/bins/{bin_id}/rejected"]
    schemas = spec["components"]["schemas"]
    assert "example" in schemas["QualityOut"]
    assert "example" in schemas["RejectedPage"]

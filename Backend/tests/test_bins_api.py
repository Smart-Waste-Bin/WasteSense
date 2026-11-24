# ruff: noqa: F811  (pytest fixtures imported from test_auth are used as arguments)
"""BE-04: bins, readings and overview API (ticket SB-11, contract v1.4 sections 5 and 6)."""

import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, insert, select

from app.core import events
from app.models import Bin, Collection, Reading, Route, Truck, User
from app.models.enums import UserRole
from tests.test_auth import START, bearer, client, fake_clock, login_as, sessions  # noqa: F401

NEW_BIN = {
    "name": "Kejetia Market",
    "location": {"lat": 6.698635, "lng": -1.61914},
    "depth_cm": 100,
    "volume_l": 240,
}


@pytest.fixture
def admin(client):
    return bearer(login_as(client, UserRole.ADMIN)["access_token"])


@pytest.fixture
def collector(client):
    return bearer(login_as(client, UserRole.COLLECTOR)["access_token"])


def add_bin(make_session, bin_id, name=None, status="normal", fill=None, seen=None, **extra):
    with make_session() as session:
        session.add(
            Bin(
                id=bin_id,
                name=name or f"Bin {bin_id}",
                location="SRID=4326;POINT(-1.5733 6.6747)",
                depth_cm=100,
                volume_l=240,
                status=status,
                last_fill=fill,
                last_seen_at=seen,
                **extra,
            )
        )
        session.commit()


def add_readings(make_session, bin_id, start, count, every=timedelta(minutes=5), fill=50):
    rows = [
        {
            "bin_id": bin_id,
            "fill": fill if callable(fill) is False else fill(i),
            "distance_cm": 50,
            "battery": 90,
            "rssi": -60,
            "seq": i,
            "device_ts": start + i * every,
            "received_at": start + i * every,
        }
        for i in range(count)
    ]
    with make_session() as session:
        session.execute(insert(Reading), rows)
        session.commit()


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


# --- Login and roles ---


def test_every_endpoint_needs_a_token(client):
    for method, path in [
        ("get", "/api/bins"),
        ("post", "/api/bins"),
        ("get", "/api/bins/BIN-001"),
        ("patch", "/api/bins/BIN-001"),
        ("delete", "/api/bins/BIN-001"),
        ("get", "/api/bins/BIN-001/readings"),
        ("get", "/api/stats/overview"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 401, (method, path)
        assert response.json()["error"]["code"] == "unauthorized"


def test_collector_gets_403_on_write_endpoints(client, sessions, collector):
    add_bin(sessions, "BIN-001")
    for response in [
        client.post("/api/bins", json=NEW_BIN, headers=collector),
        client.patch("/api/bins/BIN-001", json={"maintenance": True}, headers=collector),
        client.delete("/api/bins/BIN-001", headers=collector),
    ]:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"


def test_collector_can_read_bins_but_not_readings_or_stats(client, sessions, collector):
    add_bin(sessions, "BIN-001")
    assert client.get("/api/bins", headers=collector).status_code == 200
    assert client.get("/api/bins/BIN-001", headers=collector).status_code == 200
    assert client.get("/api/bins/BIN-001/readings", headers=collector).status_code == 403
    assert client.get("/api/stats/overview", headers=collector).status_code == 403


def test_supervisor_can_write(client):
    headers = bearer(login_as(client, UserRole.SUPERVISOR)["access_token"])
    assert client.post("/api/bins", json=NEW_BIN, headers=headers).status_code == 201


# --- Create ---


def test_create_bin_returns_location_as_lat_lng(client, admin):
    response = client.post("/api/bins", json=NEW_BIN, headers=admin)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] == "BIN-001"
    assert body["location"] == {"lat": 6.698635, "lng": -1.61914}
    assert body["status"] == "offline"  # never reported yet (D5)
    assert body["depth_cm"] == 100 and isinstance(body["depth_cm"], int)
    assert body["created_at"].endswith("Z")
    assert "deleted_at" not in body


def test_create_takes_the_next_free_id(client, sessions, admin):
    add_bin(sessions, "BIN-007")
    assert client.post("/api/bins", json=NEW_BIN, headers=admin).json()["id"] == "BIN-008"


def test_create_with_used_id_or_sensor_is_409(client, sessions, admin):
    add_bin(sessions, "BIN-001", sensor_id="ESP-1")
    used_id = client.post("/api/bins", json={**NEW_BIN, "id": "BIN-001"}, headers=admin)
    used_sensor = client.post("/api/bins", json={**NEW_BIN, "sensor_id": "ESP-1"}, headers=admin)
    assert used_id.status_code == 409
    assert used_sensor.status_code == 409
    assert used_sensor.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    "change",
    [
        {"location": {"lat": 6.7, "lon": -1.6}},  # old field name
        {"location": {"lat": 91, "lng": -1.6}},
        {"depth_cm": 0},
        {"name": ""},
        {"due_threshold": 90, "urgent_threshold": 70},
        {"id": "bin-1"},
        {"colour": "green"},
    ],
)
def test_create_rejects_bad_input(client, admin, change):
    response = client.post("/api/bins", json={**NEW_BIN, **change}, headers=admin)
    assert response.status_code == 422, change
    assert response.json()["error"]["code"] == "validation_error"


# --- Get, update, delete ---


def test_get_unknown_bin_is_404(client, admin):
    response = client.get("/api/bins/BIN-404", headers=admin)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_patch_changes_only_sent_fields_and_location(client, sessions, admin):
    add_bin(sessions, "BIN-001", name="Old name")
    response = client.patch(
        "/api/bins/BIN-001",
        json={"name": "New name", "location": {"lat": 6.7, "lng": -1.6}},
        headers=admin,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "New name"
    assert body["location"] == {"lat": 6.7, "lng": -1.6}
    assert body["volume_l"] == 240


def test_patch_maintenance_changes_status_and_emits(client, sessions, admin, fake_clock):
    add_bin(sessions, "BIN-001", status="normal", fill=10, seen=START)
    seen = []

    def listener(event_type, data):
        seen.append((event_type, data["status"]))

    events.add_listener(listener)
    try:
        response = client.patch("/api/bins/BIN-001", json={"maintenance": True}, headers=admin)
    finally:
        events.remove_listener(listener)
    assert response.json()["status"] == "maintenance"
    assert seen == [("bin_updated", "maintenance")]


def test_patch_threshold_changes_status(client, sessions, admin):
    add_bin(sessions, "BIN-001", status="filling", fill=60, seen=START)
    response = client.patch("/api/bins/BIN-001", json={"due_threshold": 55}, headers=admin)
    assert response.json()["status"] == "due"


@pytest.mark.parametrize("change", [{"name": None}, {"maintenance": None}, {"location": None}])
def test_patch_rejects_null_for_required_fields(client, sessions, admin, change):
    add_bin(sessions, "BIN-001")
    assert client.patch("/api/bins/BIN-001", json=change, headers=admin).status_code == 422


def test_delete_is_soft_and_keeps_readings(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    add_readings(sessions, "BIN-001", START - timedelta(hours=1), 3)

    response = client.delete("/api/bins/BIN-001", headers=admin)
    assert response.status_code == 204

    assert client.get("/api/bins/BIN-001", headers=admin).status_code == 404
    assert client.delete("/api/bins/BIN-001", headers=admin).status_code == 404
    assert client.get("/api/bins/BIN-001/readings", headers=admin).status_code == 404
    assert ids(client.get("/api/bins", headers=admin)) == []
    with sessions() as session:
        assert session.get(Bin, "BIN-001").deleted_at is not None
        count = session.scalar(select(func.count()).select_from(Reading))
        assert count == 3
    # A deleted bin's ID is never given out again.
    assert client.post("/api/bins", json=NEW_BIN, headers=admin).json()["id"] == "BIN-002"


# --- List: filters, search, sort, paging ---


@pytest.fixture
def five_bins(sessions):
    add_bin(sessions, "BIN-001", "KNUST Hall 7", "due", 75, START)
    add_bin(sessions, "BIN-002", "Kejetia Market", "urgent", 95, START)
    add_bin(sessions, "BIN-003", "Adum Station", "normal", 10, START)
    add_bin(sessions, "BIN-004", "Kejetia Lorry Park", "offline", None, None)
    add_bin(sessions, "BIN-005", "KNUST Library", "filling", 55, START, is_physical=True)


def test_status_filter_takes_several_values(client, admin, five_bins):
    response = client.get("/api/bins?status=due,urgent", headers=admin)
    assert ids(response) == ["BIN-001", "BIN-002"]
    assert response.json()["total"] == 2


def test_unknown_status_is_422(client, admin, five_bins):
    assert client.get("/api/bins?status=full", headers=admin).status_code == 422


def test_search_matches_id_and_name_ignoring_case(client, admin, five_bins):
    assert ids(client.get("/api/bins?q=kejetia", headers=admin)) == ["BIN-002", "BIN-004"]
    assert ids(client.get("/api/bins?q=bin-003", headers=admin)) == ["BIN-003"]
    assert ids(client.get("/api/bins?q=nothing", headers=admin)) == []


def test_filters_combine(client, admin, five_bins):
    assert ids(client.get("/api/bins?q=knust&is_physical=true", headers=admin)) == ["BIN-005"]
    assert ids(client.get("/api/bins?q=kejetia&status=offline", headers=admin)) == ["BIN-004"]


def test_sort_largest_first_puts_nulls_last(client, admin, five_bins):
    response = client.get("/api/bins?sort=-last_fill", headers=admin)
    assert ids(response) == ["BIN-002", "BIN-001", "BIN-005", "BIN-003", "BIN-004"]
    response = client.get("/api/bins?sort=name", headers=admin)
    assert ids(response) == ["BIN-003", "BIN-004", "BIN-002", "BIN-001", "BIN-005"]


def test_unknown_sort_is_422(client, admin, five_bins):
    assert client.get("/api/bins?sort=colour", headers=admin).status_code == 422


def test_paging_returns_the_right_rows_and_total(client, admin, five_bins):
    first = client.get("/api/bins?page=1&size=2", headers=admin)
    third = client.get("/api/bins?page=3&size=2", headers=admin)
    past_end = client.get("/api/bins?page=9&size=2", headers=admin)
    assert ids(first) == ["BIN-001", "BIN-002"]
    assert ids(third) == ["BIN-005"]
    assert ids(past_end) == []
    assert first.json()["total"] == third.json()["total"] == past_end.json()["total"] == 5


@pytest.mark.parametrize("query", ["page=0", "size=0", "size=101"])
def test_bad_paging_is_422(client, admin, query):
    assert client.get(f"/api/bins?{query}", headers=admin).status_code == 422


# --- Readings ---


def test_raw_readings_oldest_first_within_range(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    add_readings(sessions, "BIN-001", START - timedelta(hours=2), 24, fill=lambda i: i)

    response = client.get(
        "/api/bins/BIN-001/readings",
        params={"from": "2026-11-07T06:30:00Z", "to": "2026-11-07T07:00:00Z"},
        headers=admin,
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["fill"] for item in items] == [6, 7, 8, 9, 10, 11]  # 06:30 in, 07:00 out
    assert items[0]["ts"] == "2026-11-07T06:30:00Z"
    assert set(items[0]) == {
        "seq",
        "fill",
        "distance_cm",
        "battery",
        "rssi",
        "ts",
        "received_at",
        "is_late",
    }


def test_raw_readings_default_to_the_last_24_hours(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    add_readings(sessions, "BIN-001", START - timedelta(hours=30), 30, every=timedelta(hours=1))
    assert client.get("/api/bins/BIN-001/readings", headers=admin).json()["total"] == 24


def test_hour_bucket_gives_average_and_max_per_hour(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    # 06:00-06:55 fill 0..11, 07:00-07:55 fill 12..23
    add_readings(sessions, "BIN-001", START - timedelta(hours=2), 24, fill=lambda i: i)

    response = client.get("/api/bins/BIN-001/readings?bucket=hour", headers=admin)
    assert response.json() == {
        "items": [
            {"ts": "2026-11-07T06:00:00Z", "avg_fill": 5.5, "max_fill": 11, "count": 12},
            {"ts": "2026-11-07T07:00:00Z", "avg_fill": 17.5, "max_fill": 23, "count": 12},
        ],
        "total": 2,
    }


def test_readings_bad_input(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    url = "/api/bins/BIN-001/readings"
    assert client.get(f"{url}?bucket=day", headers=admin).status_code == 422
    assert client.get(f"{url}?size=1001", headers=admin).status_code == 422
    backwards = {"from": "2026-11-07T08:00:00Z", "to": "2026-11-07T07:00:00Z"}
    assert client.get(url, params=backwards, headers=admin).status_code == 422
    assert client.get("/api/bins/BIN-404/readings", headers=admin).status_code == 404


def test_30_days_of_hours_for_one_bin_in_under_1_second(client, sessions, admin):
    add_bin(sessions, "BIN-001")
    add_bin(sessions, "BIN-002")
    month_ago = START - timedelta(days=30)
    add_readings(sessions, "BIN-001", month_ago, 30 * 24 * 12)  # one every 5 min
    add_readings(sessions, "BIN-002", month_ago, 30 * 24 * 12)  # noise from another bin

    began = time.perf_counter()
    response = client.get(
        "/api/bins/BIN-001/readings",
        params={
            "from": month_ago.isoformat(),
            "to": START.isoformat(),
            "bucket": "hour",
            "size": 1000,
        },
        headers=admin,
    )
    took = time.perf_counter() - began

    assert response.status_code == 200
    assert response.json()["total"] == 720
    assert len(response.json()["items"]) == 720
    assert took < 1, f"took {took:.2f} s"


# --- Overview ---


def test_overview_counts(client, sessions, admin, five_bins):
    add_bin(sessions, "BIN-006", status="due", deleted_at=START)  # deleted: not counted
    with sessions() as session:
        collector_id = session.scalar(select(User.id).where(User.role == "collector"))
        truck = Truck(name="Truck 1", plate_number="AS-1-26", capacity_l=5000)
        session.add(truck)
        session.flush()

        def route(done_at, baseline, total):
            return Route(
                collector_id=collector_id,
                truck_id=truck.id,
                created_by=collector_id,
                status="completed",
                method="optimised",
                distance_source="straight_line",
                total_distance_m=total,
                est_time_s=600,
                load_l=100,
                baseline_fixed_m=baseline,
                completed_at=done_at,
            )

        # START is Saturday 7 Nov 08:00, so this week began Monday 2 Nov.
        session.add_all(
            [
                route(START - timedelta(hours=1), 10000, 7000),  # saves 3000
                route(START - timedelta(days=4), 5000, 4500),  # Tuesday: saves 500
                route(START - timedelta(days=6), 9000, 1000),  # last Sunday: not this week
                route(START - timedelta(hours=2), None, 1000),  # no baseline: left out
            ]
        )

        def collection(at):
            return Collection(
                bin_id="BIN-001",
                collector_id=collector_id,
                emptied_at=at,
                idempotency_key=uuid.uuid4(),
            )

        session.add_all(
            [
                collection(START - timedelta(hours=7)),  # 01:00 today
                collection(START - timedelta(minutes=5)),
                collection(START - timedelta(hours=9)),  # yesterday
            ]
        )
        session.commit()

    response = client.get("/api/stats/overview", headers=admin)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "total_bins": 5,
        "needing_collection": 2,
        "offline": 1,
        "collections_today": 2,
        "distance_saved_week_m": 3500,
    }


def test_overview_with_nothing_is_all_zero(client, admin):
    assert client.get("/api/stats/overview", headers=admin).json() == {
        "total_bins": 0,
        "needing_collection": 0,
        "offline": 0,
        "collections_today": 0,
        "distance_saved_week_m": 0,
    }


# --- /docs ---


def test_docs_have_every_endpoint_with_an_example(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert set(paths["/api/bins"]) == {"get", "post"}
    assert set(paths["/api/bins/{bin_id}"]) == {"get", "patch", "delete"}
    assert "get" in paths["/api/bins/{bin_id}/readings"]
    assert "get" in paths["/api/stats/overview"]
    schemas = spec["components"]["schemas"]
    for name in ["BinOut", "BinsPage", "BinCreate", "BinUpdate", "ReadingsPage", "OverviewOut"]:
        assert "example" in schemas[name], name

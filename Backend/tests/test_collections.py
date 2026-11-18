# ruff: noqa: F811  (pytest fixtures imported from test_auth are used as arguments)
"""BE-08: collection records and sensor confirmation (ticket SB-20, contract v1.6)."""

import json
import threading
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from sqlalchemy import func, select

from app.collections.service import flag_unconfirmed
from app.core import events
from app.ingest import mqtt_client
from app.ingest.service import handle_reading
from app.models import Bin, Collection, Notification, Route, RouteStop, Truck, User
from app.models.enums import UserRole
from simulator import run as sim_run
from simulator.engine import Simulation
from simulator.scenario import Scenario
from tests.test_auth import START, bearer, client, fake_clock, login_as, sessions  # noqa: F401

DOCS = Path(__file__).resolve().parents[2] / "Docs" / "contract"


def z(when):
    return when.isoformat().replace("+00:00", "Z")


@pytest.fixture
def published(monkeypatch):
    """Catch bins/{id}/emptied instead of sending it over MQTT."""
    sent = []

    def fake_publish(payload):
        sent.append(payload)
        return True

    monkeypatch.setattr(mqtt_client, "publish_emptied", fake_publish)
    return sent


@pytest.fixture
def setup(client, sessions):
    """BIN-002 at 92 %, a route for the collector with a stop at BIN-002."""
    with sessions() as session:
        session.add(
            Bin(
                id="BIN-002",
                name="Kejetia Market",
                location="SRID=4326;POINT(-1.6191 6.6986)",
                depth_cm=100,
                volume_l=240,
                last_fill=92,
                last_seen_at=START,
                status="urgent",
            )
        )
        users = {u.role: u for u in session.scalars(select(User))}
        truck = Truck(name="Truck 1", plate_number="AS-1-26", capacity_l=5000)
        session.add(truck)
        session.flush()
        route = Route(
            collector_id=users["collector"].id,
            truck_id=truck.id,
            created_by=users["supervisor"].id,
            status="in_progress",
            method="optimised",
            distance_source="straight_line",
            total_distance_m=1000,
            est_time_s=600,
            load_l=240,
        )
        session.add(route)
        session.flush()
        stop = RouteStop(route_id=route.id, bin_id="BIN-002", stop_order=1)
        session.add(stop)
        session.commit()
        ids = SimpleNamespace(
            route=route.id,
            stop=stop.id,
            collector=users["collector"].id,
            supervisor=users["supervisor"].id,
        )
    tokens = {role: bearer(login_as(client, role)["access_token"]) for role in UserRole}
    return SimpleNamespace(ids=ids, tokens=tokens)


def empty(client, setup, key=None, who=UserRole.COLLECTOR, **extra):
    body = {
        "bin_id": "BIN-002",
        "idempotency_key": str(key or uuid.uuid4()),
        "stop_id": str(setup.ids.stop),
        **extra,
    }
    return client.post("/api/collections", json=body, headers=setup.tokens[who])


def reading(seq, fill, ts):
    data = json.loads((DOCS / "examples/mqtt/reading.json").read_text(encoding="utf-8"))
    data.update(bin_id="BIN-002", seq=seq, fill=fill, distance_cm=max(100 - fill, 1), ts=z(ts))
    return json.dumps(data).encode()


def collection_row(sessions):
    with sessions() as session:
        return session.scalar(select(Collection))


# --- Acceptance 1: marking a stop emptied creates exactly one collection ---


def test_marking_a_stop_emptied_creates_exactly_one_collection(
    client, sessions, setup, published, fake_clock
):
    key = uuid.uuid4()
    first = empty(client, setup, key)
    again = empty(client, setup, key)  # the app retried (bad network)
    other_key = empty(client, setup)  # a second tap for the same stop

    assert first.status_code == 201, first.text
    assert again.status_code == 200 and other_key.status_code == 200
    assert first.json() == again.json() == other_key.json()
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(Collection)) == 1
        stop = session.get(RouteStop, setup.ids.stop)
        assert (stop.status, stop.emptied_at) == ("emptied", START)

    body = first.json()
    assert body["route_id"] == str(setup.ids.route)
    assert body["collector_id"] == str(setup.ids.collector)
    assert body["fill_before"] == 92
    assert body["confirmation"] == "waiting"
    # bins/BIN-002/emptied went out once, in the contract's shape.
    assert published == [
        {
            "bin_id": "BIN-002",
            "emptied_at": "2026-11-07T08:00:00Z",
            "route_id": str(setup.ids.route),
        }
    ]
    schema = json.loads((DOCS / "schemas/emptied.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(published[0])


def test_emptied_outside_a_route(client, sessions, setup, published):
    body = {"bin_id": "BIN-002", "idempotency_key": str(uuid.uuid4())}
    response = client.post("/api/collections", json=body, headers=setup.tokens[UserRole.COLLECTOR])
    assert response.status_code == 201
    assert response.json()["stop_id"] is None and response.json()["route_id"] is None
    assert published[0]["route_id"] is None


# --- Acceptance 2: a simulated bin resets and the collection is confirmed ---


def test_simulated_bin_resets_and_the_collection_is_confirmed(
    client, sessions, setup, published, fake_clock
):
    rows = [{"id": "BIN-002", "name": "Kejetia Market", "depth_cm": "100"}]
    sim = Simulation(rows, Scenario(fixed_seed=1), START, last_fills={"BIN-002": 92})
    simulator_mqtt = sim_run.make_client(sim, threading.Lock())

    assert empty(client, setup).status_code == 201
    # The backend's emptied message reaches the simulator, which resets the bin.
    message = SimpleNamespace(topic="bins/BIN-002/emptied", payload=json.dumps(published[0]))
    simulator_mqtt.on_message(simulator_mqtt, None, message)
    assert sim.bins["BIN-002"].fill <= 5

    # Its next reading, 5 minutes later, goes through the real ingest code.
    taken = START + timedelta(minutes=5)
    for out in sim.step(taken, z(taken)):
        with sessions() as session:
            assert (
                handle_reading(session, out.topic, json.dumps(out.payload).encode(), taken)
                == "stored"
            )

    row = collection_row(sessions)
    assert row.confirmed_by_sensor is True
    assert row.confirmed_at == taken
    listed = client.get("/api/collections", headers=setup.tokens[UserRole.SUPERVISOR]).json()
    assert listed["items"][0]["confirmation"] == "confirmed"


# --- Acceptance 3: a bin that stays full is flagged as unconfirmed ---


def test_a_bin_that_stays_full_is_flagged_and_the_supervisor_notified(
    client, sessions, setup, published, fake_clock
):
    assert empty(client, setup).status_code == 201
    with sessions() as session:
        handle_reading(
            session,
            "bins/BIN-002/readings",
            reading(1, 91, START + timedelta(minutes=5)),
            START + timedelta(minutes=5),
        )

    sent = []

    def listener(event_type, data):
        sent.append((event_type, data))

    events.add_listener(listener)
    try:
        with sessions() as session:
            assert flag_unconfirmed(session, START + timedelta(minutes=29)) == []  # not yet
            flagged = flag_unconfirmed(session, START + timedelta(minutes=31))
            assert flag_unconfirmed(session, START + timedelta(minutes=32)) == []  # only once
    finally:
        events.remove_listener(listener)

    row = collection_row(sessions)
    assert flagged == [row.id]
    assert row.confirmed_by_sensor is False
    assert row.unconfirmed_at == START + timedelta(minutes=31)
    with sessions() as session:
        notes = session.scalars(select(Notification)).all()
    assert [n.user_id for n in notes] == [setup.ids.supervisor]  # supervisors only
    assert notes[0].type == "collection_unconfirmed"
    assert "91" in notes[0].body
    assert notes[0].data == {"collection_id": str(row.id), "bin_id": "BIN-002"}
    # Also live over the WebSocket, to that supervisor (BE-05 sends notifications by user_id).
    assert [(t, d["user_id"]) for t, d in sent] == [("notification", str(setup.ids.supervisor))]
    response = client.get(
        "/api/collections?confirmation=unconfirmed", headers=setup.tokens[UserRole.SUPERVISOR]
    )
    assert response.json()["total"] == 1


# --- The confirmation rule ---


@pytest.mark.parametrize(
    ("fill", "minutes", "confirmed"),
    [
        (19, 5, True),  # under 20 %
        (20, 5, True),  # not under 20, but a drop of 72 (92 -> 20)
        (52, 5, True),  # a drop of 40 (92 -> 52)
        (53, 5, False),  # a drop of 39
        (5, 30, True),  # exactly 30 minutes is still within
        (5, 31, False),  # too late to count
        (5, -1, False),  # taken before the emptying
    ],
)
def test_confirmation_rule(
    client, sessions, setup, published, fake_clock, fill, minutes, confirmed
):
    assert empty(client, setup).status_code == 201
    taken = START + timedelta(minutes=minutes)
    with sessions() as session:
        result = handle_reading(
            session,
            "bins/BIN-002/readings",
            reading(1, fill, taken),
            max(taken, START) + timedelta(seconds=1),
        )
    assert result == "stored"
    assert collection_row(sessions).confirmed_by_sensor is confirmed


def test_a_late_reading_can_still_confirm_a_flagged_collection(
    client, sessions, setup, published, fake_clock
):
    assert empty(client, setup).status_code == 201
    with sessions() as session:
        flag_unconfirmed(session, START + timedelta(minutes=31))
        # Taken 10 minutes after emptying, delivered late after an outage.
        handle_reading(
            session,
            "bins/BIN-002/readings",
            reading(1, 3, START + timedelta(minutes=10)),
            START + timedelta(minutes=40),
        )
    row = collection_row(sessions)
    assert row.confirmed_by_sensor is True and row.unconfirmed_at is not None


# --- Who can record, and bad requests ---


def test_a_collector_cant_empty_a_stop_on_another_collectors_route(
    client, sessions, setup, published
):
    with sessions() as session:
        session.get(Route, setup.ids.route).collector_id = setup.ids.supervisor
        session.commit()
    assert empty(client, setup).status_code == 403
    assert empty(client, setup, who=UserRole.SUPERVISOR).status_code == 201  # staff may
    assert len(published) == 1


def test_bad_collection_requests(client, sessions, setup, published, fake_clock):
    key = uuid.uuid4()
    assert empty(client, setup, key).status_code == 201
    with sessions() as session:
        session.add(
            Bin(
                id="BIN-003",
                name="Adum",
                location="SRID=4326;POINT(-1.62 6.69)",
                depth_cm=100,
                volume_l=240,
            )
        )
        session.commit()
    same_key_other_bin = client.post(
        "/api/collections",
        json={"bin_id": "BIN-003", "idempotency_key": str(key)},
        headers=setup.tokens[UserRole.COLLECTOR],
    )
    assert same_key_other_bin.status_code == 409
    assert empty(client, setup, bin_id="BIN-404").status_code == 404
    assert empty(client, setup, bin_id="BIN-003").status_code == 422  # stop is for BIN-002
    assert empty(client, setup, stop_id=str(uuid.uuid4())).status_code == 404
    future = z(START + timedelta(hours=1))
    assert empty(client, setup, emptied_at=future).status_code == 422
    assert empty(client, setup, idempotency_key="not-a-uuid").status_code == 422
    assert client.post("/api/collections", json={}).status_code == 401
    assert len(published) == 1


# --- History ---


def test_collection_history_filters_and_roles(client, sessions, setup, published, fake_clock):
    empty(client, setup)
    for _ in range(2):  # two more outside the route, an hour earlier
        client.post(
            "/api/collections",
            json={
                "bin_id": "BIN-002",
                "idempotency_key": str(uuid.uuid4()),
                "emptied_at": z(START - timedelta(hours=1)),
            },
            headers=setup.tokens[UserRole.COLLECTOR],
        )
    staff = setup.tokens[UserRole.SUPERVISOR]
    everything = client.get("/api/collections", headers=staff).json()
    assert everything["total"] == 3
    assert everything["items"][0]["emptied_at"] == "2026-11-07T08:00:00Z"  # newest first
    in_range = client.get(
        "/api/collections", params={"from": z(START - timedelta(minutes=5))}, headers=staff
    ).json()
    assert in_range["total"] == 1
    assert client.get("/api/collections?bin_id=BIN-003", headers=staff).json()["total"] == 0
    assert client.get("/api/collections?confirmation=waiting", headers=staff).json()["total"] == 3
    assert client.get("/api/collections?confirmation=maybe", headers=staff).status_code == 422
    assert (
        client.get("/api/collections", headers=setup.tokens[UserRole.COLLECTOR]).status_code == 403
    )


def test_docs_have_examples(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ["CollectionIn", "CollectionOut", "CollectionsPage"]:
        assert "example" in schemas[name], name

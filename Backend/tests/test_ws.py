# ruff: noqa: F811  (pytest fixtures imported from test_auth are used as arguments)
"""BE-05: WebSocket live updates (ticket SB-17, contract section 7)."""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.core import events
from app.core.security import hash_password
from app.ingest.service import handle_reading
from app.main import app
from app.models import Bin, User
from app.models.enums import UserRole
from app.realtime.hub import hub
from tests.test_auth import client, fake_clock, login_as, sessions  # noqa: F401

DOCS = Path(__file__).resolve().parents[2] / "Docs" / "contract" / "examples"
OTHER_COLLECTOR = {"email": "collector2@smartbin.test", "password": "collector2-pass-123"}


@pytest.fixture(autouse=True)
def quick_ping(monkeypatch):
    # A missing event shows up as a ping instead of a test that hangs forever.
    monkeypatch.setattr(settings, "ws_ping_interval_s", 0.3)


@pytest.fixture
def tokens(client, sessions):
    with sessions() as session:
        session.add(
            User(
                name="Collector Two",
                email=OTHER_COLLECTOR["email"],
                phone="+233200000004",
                role=UserRole.COLLECTOR,
                password_hash=hash_password(OTHER_COLLECTOR["password"]),
            )
        )
        session.commit()
    other = client.post(
        "/api/auth/login",
        json={"login": OTHER_COLLECTOR["email"], "password": OTHER_COLLECTOR["password"]},
    ).json()
    result = {role.value: login_as(client, role) for role in UserRole}
    result["collector2"] = other
    return result


def token(tokens, who):
    return tokens[who]["access_token"]


def user_id(tokens, who):
    return tokens[who]["user"]["id"]


def connect(client, tokens, who):
    return client.websocket_connect(f"/ws?token={token(tokens, who)}")


def ready(ws):
    """The first ping proves the server has checked the token and registered the client."""
    assert ws.receive_json() == {"type": "ping"}
    return ws


def receive_closed_code(client, url):
    with client.websocket_connect(url) as ws:
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
    return closed.value.code


# --- Login ---


@pytest.mark.parametrize("url", ["/ws", "/ws?token=", "/ws?token=not-a-token"])
def test_bad_or_missing_token_is_closed_with_4401(client, url):
    assert receive_closed_code(client, url) == 4401


def test_refresh_token_is_not_accepted(client, tokens):
    refresh = tokens["admin"]["refresh_token"]
    assert receive_closed_code(client, f"/ws?token={refresh}") == 4401


def test_expired_token_is_closed_with_4401(client, tokens, fake_clock):
    fake_clock.move(hours=2)
    assert receive_closed_code(client, f"/ws?token={token(tokens, 'admin')}") == 4401


def test_deactivated_user_is_closed_with_4401(client, tokens, sessions):
    with sessions() as session:
        session.get(User, user_id(tokens, "collector")).is_active = False
        session.commit()
    assert receive_closed_code(client, f"/ws?token={token(tokens, 'collector')}") == 4401


# --- Heartbeat ---


def test_heartbeat_is_a_bare_ping(client, tokens):
    with connect(client, tokens, "supervisor") as ws:
        assert ws.receive_json() == {"type": "ping"}
        assert ws.receive_json() == {"type": "ping"}


def test_ping_every_25_seconds_by_default():
    assert type(settings).model_fields["ws_ping_interval_s"].default == 25


# --- A new reading reaches a connected client ---


@pytest.fixture
def bin_001(sessions):
    with sessions() as session:
        session.add(
            Bin(
                id="BIN-001",
                name="KNUST",
                location="SRID=4326;POINT(-1.5733 6.6747)",
                depth_cm=100,
                volume_l=240,
            )
        )
        session.commit()


def test_new_reading_reaches_a_client_within_2_seconds(
    client, tokens, sessions, bin_001, fake_clock
):
    fake_clock.move(minutes=31)  # the example reading is from 08:30
    payload = (DOCS / "mqtt/reading.json").read_bytes()
    example = json.loads((DOCS / "ws/bin_updated.json").read_text(encoding="utf-8"))

    with connect(client, tokens, "supervisor") as ws:
        ready(ws)
        began = time.perf_counter()
        with sessions() as session:
            assert handle_reading(session, "bins/BIN-001/readings", payload, fake_clock.now()) == (
                "stored"
            )
        message = ws.receive_json()
        took = time.perf_counter() - began

    assert took < 2
    assert message["type"] == "bin_updated"
    # last_seen_at is when the server got it (08:31), not the device time (08:30).
    assert message["data"] == {**example["data"], "last_seen_at": "2026-11-07T08:31:00Z"}
    assert message["ts"] == "2026-11-07T08:31:00Z"


# --- Who gets what ---


def route_event(collector_id):
    return {"id": "route-1", "status": "in_progress", "collector_id": collector_id}


def test_collector_gets_only_their_own_route_and_notifications(client, tokens):
    me, other = user_id(tokens, "collector"), user_id(tokens, "collector2")
    with connect(client, tokens, "collector") as ws:
        ready(ws)
        events.emit("bin_updated", {"id": "BIN-001"})
        events.emit("alert_created", {"id": 1})
        events.emit("collector_location", {"collector_id": me})
        events.emit("route_updated", route_event(other))
        events.emit("notification", {"id": 2, "user_id": other})
        events.emit("route_updated", route_event(me))
        events.emit("notification", {"id": 3, "user_id": me, "title": "New route"})

        # Events arrive in order, so if any other one had been sent it would come first.
        first, second, third = ws.receive_json(), ws.receive_json(), ws.receive_json()

    assert first["type"] == "route_updated" and first["data"]["collector_id"] == me
    # user_id is only for routing; the contract's notification has no user_id.
    assert second == {
        "type": "notification",
        "data": {"id": 3, "title": "New route"},
        "ts": second["ts"],
    }
    assert third == {"type": "ping"}


def test_supervisor_gets_every_event_but_only_their_own_notifications(client, tokens):
    collector = user_id(tokens, "collector")
    sent = [
        ("bin_updated", {"id": "BIN-001"}),
        ("alert_created", {"id": 1}),
        ("alert_updated", {"id": 1}),
        ("route_updated", route_event(collector)),
        ("collector_location", {"collector_id": collector}),
    ]
    with connect(client, tokens, "supervisor") as ws:
        ready(ws)
        events.emit("notification", {"id": 9, "user_id": collector})
        for event_type, data in sent:
            events.emit(event_type, data)
        events.emit("notification", {"id": 10, "user_id": user_id(tokens, "supervisor")})
        got = [ws.receive_json() for _ in range(len(sent) + 1)]

    assert [(m["type"], m["data"]) for m in got[:-1]] == sent
    assert got[-1]["type"] == "notification" and got[-1]["data"] == {"id": 10}
    assert all(m["ts"].endswith("Z") for m in got)


def test_admin_gets_staff_events(client, tokens):
    with connect(client, tokens, "admin") as ws:
        ready(ws)
        events.emit("bin_updated", {"id": "BIN-001"})
        assert ws.receive_json()["type"] == "bin_updated"


def test_one_event_reaches_every_connected_client(client, tokens):
    with connect(client, tokens, "admin") as one, connect(client, tokens, "supervisor") as two:
        ready(one)
        ready(two)
        events.emit("bin_updated", {"id": "BIN-001"})
        assert one.receive_json()["data"] == two.receive_json()["data"] == {"id": "BIN-001"}


# --- Leaving, and the server restarting ---


def test_client_is_forgotten_when_it_disconnects(client, tokens):
    with connect(client, tokens, "supervisor") as ws:
        ws.receive_json()  # wait until it is fully connected
        assert hub.count() == 1
    deadline = time.time() + 2
    while hub.count() and time.time() < deadline:
        time.sleep(0.05)
    assert hub.count() == 0
    events.emit("bin_updated", {"id": "BIN-001"})  # nobody listening: must not fail


def test_client_can_reconnect_after_the_server_restarts(client, tokens, fake_clock):
    with connect(client, tokens, "supervisor") as ws:
        ws.receive_json()

    # Stop the app (lifespan shutdown) and start it again, like a server restart.
    client.__exit__(None, None, None)
    with TestClient(app) as restarted:
        with restarted.websocket_connect(f"/ws?token={token(tokens, 'supervisor')}") as ws:
            ready(ws)
            events.emit("bin_updated", {"id": "BIN-002"})
            assert ws.receive_json()["data"] == {"id": "BIN-002"}

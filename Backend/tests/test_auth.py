import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db, require_role
from app.core import clock
from app.core.errors import add_error_handlers
from app.core.security import hash_password
from app.main import app
from app.models import RefreshToken, User
from app.models.enums import UserRole

PASSWORDS = {
    UserRole.ADMIN: "admin-pass-123",
    UserRole.SUPERVISOR: "supervisor-pass-123",
    UserRole.COLLECTOR: "collector-pass-123",
}
PHONES = {
    UserRole.ADMIN: "+233200000001",
    UserRole.SUPERVISOR: "+233241234567",
    UserRole.COLLECTOR: "+233200000003",
}
START = datetime(2026, 11, 7, 8, 0, tzinfo=UTC)

# A route that exists only in the tests, to prove the write rule before bin routes exist.
protected_app = FastAPI()
add_error_handlers(protected_app)


@protected_app.post("/test/bins", dependencies=[Depends(require_role("admin", "supervisor"))])
def fake_bin_write():
    return {"ok": True}


class FakeClock:
    def __init__(self):
        self.time = START

    def now(self):
        return self.time

    def move(self, **kwargs):
        self.time += timedelta(**kwargs)


@pytest.fixture
def fake_clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(clock, "now", fake.now)
    return fake


@pytest.fixture
def sessions(migrated_engine):
    """Seed one user per role, and point the app at the test database."""
    make_session = sessionmaker(migrated_engine)
    with make_session() as session:
        for role, password in PASSWORDS.items():
            session.add(
                User(
                    name=role.value.title(),
                    email=f"{role.value}@smartbin.test",
                    phone=PHONES[role],
                    role=role,
                    password_hash=hash_password(password),
                )
            )
        session.commit()

    def test_db():
        with make_session() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    protected_app.dependency_overrides[get_db] = test_db
    yield make_session
    app.dependency_overrides.clear()
    protected_app.dependency_overrides.clear()


@pytest.fixture
def client(sessions, fake_clock):
    with TestClient(app) as test_client:
        yield test_client


def login(client, login, password):
    return client.post("/api/auth/login", json={"login": login, "password": password})


def login_as(client, role):
    response = login(client, f"{role.value}@smartbin.test", PASSWORDS[role])
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def get_user(sessions, email) -> User:
    with sessions() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        session.expunge(user)
        return user


def set_user(sessions, email, **values):
    with sessions() as session:
        user = session.scalar(select(User).where(User.email == email))
        for field, value in values.items():
            setattr(user, field, value)
        session.commit()


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


def test_login_with_email(client):
    body = login_as(client, UserRole.SUPERVISOR)
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["refresh_token"]
    assert body["user"] == {
        "id": body["user"]["id"],
        "name": "Supervisor",
        "email": "supervisor@smartbin.test",
        "phone": "+233241234567",
        "role": "supervisor",
    }


def test_login_email_is_not_case_sensitive(client):
    response = login(client, "  Supervisor@SmartBin.TEST ", PASSWORDS[UserRole.SUPERVISOR])
    assert response.status_code == 200


@pytest.mark.parametrize("phone", ["0241234567", "+233241234567", "024 123 4567", "233241234567"])
def test_login_with_phone(client, phone):
    response = login(client, phone, PASSWORDS[UserRole.SUPERVISOR])
    assert response.status_code == 200, response.text
    assert response.json()["user"]["phone"] == "+233241234567"


def test_login_sets_refresh_cookie(client):
    response = login(client, "supervisor@smartbin.test", PASSWORDS[UserRole.SUPERVISOR])
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"refresh_token={response.json()['refresh_token']};")
    assert "HttpOnly" in cookie
    assert "Path=/api/auth" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=604800" in cookie


def test_wrong_password(client):
    response = login(client, "supervisor@smartbin.test", "not-the-password")
    assert_error(response, 401, "invalid_credentials")
    assert response.json()["error"]["message"] == "Wrong email/phone or password"


@pytest.mark.parametrize("unknown", ["nobody@smartbin.test", "0559999999", "not-a-login"])
def test_unknown_user_gets_the_same_401(client, unknown):
    wrong_password = login(client, "supervisor@smartbin.test", "not-the-password").json()
    response = login(client, unknown, "whatever-123")
    assert_error(response, 401, "invalid_credentials")
    assert response.json() == wrong_password


def test_deactivated_user(client, sessions):
    set_user(sessions, "collector@smartbin.test", is_active=False)
    response = login(client, "collector@smartbin.test", PASSWORDS[UserRole.COLLECTOR])
    assert_error(response, 403, "account_disabled")


def test_deactivated_user_with_wrong_password_gets_401(client, sessions):
    # Don't tell someone who doesn't know the password that the account exists.
    set_user(sessions, "collector@smartbin.test", is_active=False)
    response = login(client, "collector@smartbin.test", "not-the-password")
    assert_error(response, 401, "invalid_credentials")


def fail_logins(client, times, email="supervisor@smartbin.test"):
    return [login(client, email, "not-the-password") for _ in range(times)]


def test_five_wrong_passwords_lock_the_account(client, fake_clock):
    responses = fail_logins(client, 5)
    assert [r.status_code for r in responses] == [401, 401, 401, 401, 423]
    assert_error(responses[-1], 423, "account_locked")
    assert "08:10 UTC" in responses[-1].json()["error"]["message"]

    response = login(client, "supervisor@smartbin.test", PASSWORDS[UserRole.SUPERVISOR])
    assert_error(response, 423, "account_locked")


def test_login_works_again_after_the_lock_time(client, fake_clock):
    fail_logins(client, 5)
    fake_clock.move(minutes=9, seconds=59)
    response = login(client, "supervisor@smartbin.test", PASSWORDS[UserRole.SUPERVISOR])
    assert_error(response, 423, "account_locked")

    fake_clock.move(seconds=1)
    response = login(client, "supervisor@smartbin.test", PASSWORDS[UserRole.SUPERVISOR])
    assert response.status_code == 200


def test_correct_login_resets_the_counter(client, sessions):
    fail_logins(client, 4)
    assert get_user(sessions, "supervisor@smartbin.test").failed_login_count == 4
    login_as(client, UserRole.SUPERVISOR)
    user = get_user(sessions, "supervisor@smartbin.test")
    assert user.failed_login_count == 0
    assert user.first_failed_login_at is None

    assert [r.status_code for r in fail_logins(client, 4)] == [401] * 4


def test_failures_outside_the_window_do_not_add_up(client, fake_clock):
    fail_logins(client, 4)
    fake_clock.move(minutes=11)
    assert [r.status_code for r in fail_logins(client, 4)] == [401] * 4


def test_failed_logins_for_unknown_users_are_not_stored(client, sessions):
    fail_logins(client, 6, email="nobody@smartbin.test")
    with sessions() as session:
        counts = session.scalars(select(User.failed_login_count)).all()
    assert counts == [0, 0, 0]


def test_me(client):
    tokens = login_as(client, UserRole.COLLECTOR)
    response = client.get("/api/me", headers=bearer(tokens["access_token"]))
    assert response.status_code == 200
    me = response.json()
    assert set(me) == {"id", "name", "email", "phone", "role", "is_active", "created_at"}
    assert me["role"] == "collector"
    assert me["created_at"].endswith("Z")


def test_me_without_token(client):
    assert_error(client.get("/api/me"), 401, "unauthorized")


def test_me_with_refresh_token_as_bearer(client):
    tokens = login_as(client, UserRole.COLLECTOR)
    response = client.get("/api/me", headers=bearer(tokens["refresh_token"]))
    assert_error(response, 401, "invalid_token")


def test_me_with_a_tampered_token(client):
    token = login_as(client, UserRole.COLLECTOR)["access_token"]
    response = client.get("/api/me", headers=bearer(token[:-2] + "xx"))
    assert_error(response, 401, "invalid_token")


def test_expired_access_token(client, fake_clock):
    tokens = login_as(client, UserRole.COLLECTOR)
    fake_clock.move(minutes=59)
    assert client.get("/api/me", headers=bearer(tokens["access_token"])).status_code == 200
    fake_clock.move(minutes=1)
    response = client.get("/api/me", headers=bearer(tokens["access_token"]))
    assert_error(response, 401, "token_expired")


def test_deactivated_user_token_stops_working(client, sessions):
    tokens = login_as(client, UserRole.COLLECTOR)
    set_user(sessions, "collector@smartbin.test", is_active=False)
    response = client.get("/api/me", headers=bearer(tokens["access_token"]))
    assert_error(response, 403, "account_disabled")


def test_refresh_with_body_returns_new_tokens(client, fake_clock):
    tokens = login_as(client, UserRole.SUPERVISOR)
    fake_clock.move(minutes=61)  # the access token has expired
    client.cookies.clear()
    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200, response.text
    new = response.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert new["access_token"] != tokens["access_token"]
    assert client.get("/api/me", headers=bearer(new["access_token"])).status_code == 200

    again = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(again, 401, "invalid_refresh_token")


def test_refresh_with_cookie(client):
    tokens = login_as(client, UserRole.SUPERVISOR)  # the client keeps the cookie
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200, response.text
    new = response.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert f"refresh_token={new['refresh_token']};" in response.headers["set-cookie"]


def test_refresh_rotation_links_old_to_new(client, sessions):
    tokens = login_as(client, UserRole.SUPERVISOR)
    client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    with sessions() as session:
        rows = session.scalars(select(RefreshToken).order_by(RefreshToken.created_at)).all()
        old, new = rows
        assert old.revoked_at is not None
        assert old.replaced_by == new.id
        assert new.revoked_at is None


def test_reusing_an_old_refresh_token_revokes_everything(client, sessions):
    first = login_as(client, UserRole.SUPERVISOR)
    other_device = login_as(client, UserRole.SUPERVISOR)
    client.cookies.clear()
    rotated = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200

    replay = client.post("/api/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert_error(replay, 401, "invalid_refresh_token")

    for token in [rotated.json()["refresh_token"], other_device["refresh_token"]]:
        response = client.post("/api/auth/refresh", json={"refresh_token": token})
        assert_error(response, 401, "invalid_refresh_token")
    with sessions() as session:
        assert session.scalars(select(RefreshToken.revoked_at)).all().count(None) == 0


def test_expired_refresh_token(client, fake_clock):
    tokens = login_as(client, UserRole.SUPERVISOR)
    client.cookies.clear()
    fake_clock.move(days=7)
    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(response, 401, "invalid_refresh_token")


def test_unknown_or_missing_refresh_token(client):
    unknown = client.post("/api/auth/refresh", json={"refresh_token": "made-up"})
    assert_error(unknown, 401, "invalid_refresh_token")
    assert_error(client.post("/api/auth/refresh"), 401, "invalid_refresh_token")


def test_refresh_for_deactivated_user(client, sessions):
    tokens = login_as(client, UserRole.COLLECTOR)
    set_user(sessions, "collector@smartbin.test", is_active=False)
    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(response, 403, "account_disabled")


def test_logout_revokes_the_token_and_clears_the_cookie(client):
    tokens = login_as(client, UserRole.SUPERVISOR)
    response = client.post("/api/auth/logout", headers=bearer(tokens["access_token"]))
    assert response.status_code == 204
    cookie = response.headers["set-cookie"]
    assert cookie.startswith('refresh_token="";') and "Max-Age=0" in cookie
    assert "Path=/api/auth" in cookie

    client.cookies.clear()
    again = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(again, 401, "invalid_refresh_token")


def test_logout_with_token_in_body(client):
    tokens = login_as(client, UserRole.COLLECTOR)
    client.cookies.clear()
    response = client.post(
        "/api/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=bearer(tokens["access_token"]),
    )
    assert response.status_code == 204
    again = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert_error(again, 401, "invalid_refresh_token")


def test_logout_all_devices(client):
    phone = login_as(client, UserRole.COLLECTOR)
    laptop = login_as(client, UserRole.COLLECTOR)
    client.cookies.clear()
    response = client.post(
        "/api/auth/logout", json={"all_devices": True}, headers=bearer(laptop["access_token"])
    )
    assert response.status_code == 204
    for token in [phone["refresh_token"], laptop["refresh_token"]]:
        again = client.post("/api/auth/refresh", json={"refresh_token": token})
        assert_error(again, 401, "invalid_refresh_token")


def test_logout_needs_an_access_token(client):
    assert_error(client.post("/api/auth/logout"), 401, "unauthorized")


def test_logout_cannot_revoke_another_users_token(client):
    collector = login_as(client, UserRole.COLLECTOR)
    supervisor = login_as(client, UserRole.SUPERVISOR)
    client.cookies.clear()
    client.post(
        "/api/auth/logout",
        json={"refresh_token": supervisor["refresh_token"]},
        headers=bearer(collector["access_token"]),
    )
    response = client.post("/api/auth/refresh", json={"refresh_token": supervisor["refresh_token"]})
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("role", "status"),
    [(UserRole.COLLECTOR, 403), (UserRole.SUPERVISOR, 200), (UserRole.ADMIN, 200)],
)
def test_write_rule(client, role, status):
    token = login_as(client, role)["access_token"]
    with TestClient(protected_app) as test_client:
        response = test_client.post("/test/bins", headers=bearer(token))
    assert response.status_code == status
    if status == 403:
        assert_error(response, 403, "forbidden")


def test_write_rule_without_token(client):
    with TestClient(protected_app) as test_client:
        assert_error(test_client.post("/test/bins"), 401, "unauthorized")


def test_database_holds_only_hashes(client, sessions):
    tokens = login_as(client, UserRole.SUPERVISOR)
    with sessions() as session:
        user = session.scalar(select(User).where(User.email == "supervisor@smartbin.test"))
        assert user is not None
        assert user.password_hash != PASSWORDS[UserRole.SUPERVISOR]
        assert user.password_hash.startswith("$argon2")
        stored = session.scalars(select(RefreshToken.token_hash)).all()
    assert tokens["refresh_token"] not in stored
    assert all(len(value) == 64 for value in stored)  # SHA-256 hex


def test_login_logs_contain_no_password_or_tokens(client, caplog):
    caplog.set_level(logging.DEBUG)
    # Show SQL with parameters too, the most likely place for a secret to leak.
    caplog.set_level(logging.DEBUG, logger="sqlalchemy.engine")
    tokens = login_as(client, UserRole.SUPERVISOR)
    new = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    login(client, "supervisor@smartbin.test", "wrong-password-xyz")
    client.post("/api/auth/login", json={"password": "missing-login-field"})

    assert caplog.text, "nothing was logged, so this test would prove nothing"
    for secret in [
        PASSWORDS[UserRole.SUPERVISOR],
        "wrong-password-xyz",
        "missing-login-field",
        tokens["access_token"],
        tokens["refresh_token"],
        new["access_token"],
        new["refresh_token"],
    ]:
        assert secret not in caplog.text


def test_validation_error_does_not_echo_the_password(client):
    response = client.post("/api/auth/login", json={"password": "secret-in-body"})
    assert_error(response, 422, "validation_error")
    assert "secret-in-body" not in response.text


def test_short_jwt_secret_refuses_to_start():
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(jwt_secret="too-short")


def test_wildcard_cors_origin_is_refused():
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError, match=r"not '\*'"):
        Settings(cors_origins="*")


def test_cors_allows_credentials_for_listed_origins():
    origin = "http://localhost:5173"
    response = TestClient(app).options(
        "/api/auth/login",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"

    other = TestClient(app).options(
        "/api/auth/login",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in other.headers

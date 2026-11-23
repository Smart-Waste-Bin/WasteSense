# ruff: noqa: F811  (pytest fixtures imported from test_auth are used as arguments)
"""AUTH-03: update my profile, change my password, profile photo (contract v1.7 section 5)."""

import pytest

from app.api import me as me_api
from app.config import settings
from app.core import storage
from app.models.enums import UserRole
from tests.test_auth import (  # noqa: F401
    PASSWORDS,
    assert_error,
    bearer,
    client,
    fake_clock,
    get_user,
    login,
    login_as,
    sessions,
)

SUPERVISOR_EMAIL = "supervisor@smartbin.test"
SUPERVISOR_PASSWORD = PASSWORDS[UserRole.SUPERVISOR]
NEW_PASSWORD = "new-password-456"

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


@pytest.fixture(autouse=True)
def local_media(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "media_dir", tmp_path)
    return tmp_path


@pytest.fixture
def supervisor(client):
    return bearer(login_as(client, UserRole.SUPERVISOR)["access_token"])


def change_password(client, headers, current, new, confirm=None):
    body = {
        "current_password": current,
        "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    }
    return client.post("/api/me/password", json=body, headers=headers)


def upload(client, headers, data, name="me.png"):
    return client.put("/api/me/photo", files={"photo": (name, data)}, headers=headers)


# --- Profile ---


def test_me_has_photo_url(client, supervisor):
    body = client.get("/api/me", headers=supervisor).json()
    assert body["photo_url"] is None
    assert "photo_key" not in body


def test_update_name_and_phone_shows_in_me_at_once(client, supervisor):
    response = client.patch(
        "/api/me", json={"name": "  Ama Mensah ", "phone": "024 555 1234"}, headers=supervisor
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Ama Mensah"
    assert response.json()["phone"] == "+233245551234"
    me = client.get("/api/me", headers=supervisor).json()
    assert (me["name"], me["phone"]) == ("Ama Mensah", "+233245551234")


def test_update_only_what_is_sent(client, supervisor):
    client.patch("/api/me", json={"name": "New Name"}, headers=supervisor)
    me = client.get("/api/me", headers=supervisor).json()
    assert me["phone"] == "+233241234567"


def test_phone_can_be_removed(client, supervisor):
    response = client.patch("/api/me", json={"phone": None}, headers=supervisor)
    assert response.json()["phone"] is None


def test_bad_phone_and_empty_name_are_refused(client, supervisor):
    assert_error(
        client.patch("/api/me", json={"phone": "12345"}, headers=supervisor),
        422,
        "validation_error",
    )
    assert_error(
        client.patch("/api/me", json={"name": "  "}, headers=supervisor), 422, "validation_error"
    )


def test_phone_of_another_user_is_a_conflict(client, supervisor):
    response = client.patch("/api/me", json={"phone": "+233200000001"}, headers=supervisor)
    assert_error(response, 409, "conflict")


def test_email_and_role_cannot_be_changed(client, supervisor):
    client.patch("/api/me", json={"email": "x@y.z", "role": "admin"}, headers=supervisor)
    me = client.get("/api/me", headers=supervisor).json()
    assert (me["email"], me["role"]) == (SUPERVISOR_EMAIL, "supervisor")


def test_profile_needs_login(client):
    assert_error(client.patch("/api/me", json={"name": "x"}), 401, "unauthorized")


# --- Password ---


def test_change_password(client, supervisor):
    response = change_password(client, supervisor, SUPERVISOR_PASSWORD, NEW_PASSWORD)
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
    assert login(client, SUPERVISOR_EMAIL, NEW_PASSWORD).status_code == 200
    assert_error(login(client, SUPERVISOR_EMAIL, SUPERVISOR_PASSWORD), 401, "invalid_credentials")


def test_wrong_current_password_is_refused(client, supervisor, sessions):
    response = change_password(client, supervisor, "not-my-password", NEW_PASSWORD)
    assert_error(response, 400, "wrong_password")
    assert login(client, SUPERVISOR_EMAIL, SUPERVISOR_PASSWORD).status_code == 200


def test_wrong_current_password_counts_towards_lockout(client, supervisor):
    for _ in range(4):
        assert_error(
            change_password(client, supervisor, "guess", NEW_PASSWORD), 400, "wrong_password"
        )
    assert_error(change_password(client, supervisor, "guess", NEW_PASSWORD), 423, "account_locked")
    # Locked: even the right password is refused until the lock ends.
    response = change_password(client, supervisor, SUPERVISOR_PASSWORD, NEW_PASSWORD)
    assert_error(response, 423, "account_locked")


def test_new_password_needs_8_characters(client, supervisor):
    response = change_password(client, supervisor, SUPERVISOR_PASSWORD, "short")
    assert_error(response, 422, "validation_error")
    assert "8 characters" in response.json()["error"]["message"]


def test_confirm_must_match(client, supervisor):
    response = change_password(client, supervisor, SUPERVISOR_PASSWORD, NEW_PASSWORD, "other-pass")
    assert_error(response, 422, "validation_error")


def test_change_password_logs_out_other_devices(client):
    other_device = login_as(client, UserRole.SUPERVISOR)
    this_device = login_as(client, UserRole.SUPERVISOR)
    response = change_password(
        client, bearer(this_device["access_token"]), SUPERVISOR_PASSWORD, NEW_PASSWORD
    )
    assert response.status_code == 200
    old = client.post("/api/auth/refresh", json={"refresh_token": other_device["refresh_token"]})
    assert_error(old, 401, "invalid_refresh_token")
    new = client.post("/api/auth/refresh", json={"refresh_token": response.json()["refresh_token"]})
    assert new.status_code == 200


# --- Photo ---


def test_upload_photo_local(client, supervisor, local_media, sessions):
    response = upload(client, supervisor, PNG)
    assert response.status_code == 200, response.text
    url = response.json()["photo_url"]
    assert url.startswith("/media/profile-photos/") and url.endswith(".png")

    key = get_user(sessions, SUPERVISOR_EMAIL).photo_key
    assert (local_media / key).read_bytes() == PNG
    assert client.get("/api/me", headers=supervisor).json()["photo_url"] == url


def test_new_photo_replaces_the_old_file(client, supervisor, local_media, sessions):
    upload(client, supervisor, PNG)
    first = get_user(sessions, SUPERVISOR_EMAIL).photo_key
    response = upload(client, supervisor, JPEG, "me.jpg")
    assert response.json()["photo_url"].endswith(".jpg")
    assert not (local_media / first).exists()


def test_delete_photo(client, supervisor, local_media, sessions):
    upload(client, supervisor, PNG)
    key = get_user(sessions, SUPERVISOR_EMAIL).photo_key
    response = client.delete("/api/me/photo", headers=supervisor)
    assert response.status_code == 200
    assert response.json()["photo_url"] is None
    assert not (local_media / key).exists()


def test_photo_must_be_an_image(client, supervisor):
    response = upload(client, supervisor, b"<script>alert(1)</script>", "me.png")
    assert_error(response, 422, "validation_error")


def test_photo_max_2_mb(client, supervisor):
    big = PNG + b"\x00" * me_api.MAX_PHOTO_BYTES
    assert_error(upload(client, supervisor, big), 422, "validation_error")


def test_photo_needs_login(client):
    assert_error(client.put("/api/me/photo", files={"photo": ("me.png", PNG)}), 401, "unauthorized")


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)

    def generate_presigned_url(self, method, Params, ExpiresIn):
        return f"https://{Params['Bucket']}.s3.amazonaws.com/{Params['Key']}?expires={ExpiresIn}"


def test_upload_photo_s3(client, supervisor, monkeypatch, sessions):
    s3 = FakeS3()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "smartbin-photos")
    monkeypatch.setattr(storage, "_s3_client", lambda: s3)

    response = upload(client, supervisor, JPEG, "me.jpg")
    assert response.status_code == 200, response.text
    key = get_user(sessions, SUPERVISOR_EMAIL).photo_key
    assert s3.objects[("smartbin-photos", key)] == (JPEG, "image/jpeg")
    assert response.json()["photo_url"] == (
        f"https://smartbin-photos.s3.amazonaws.com/{key}?expires=3600"
    )

    client.delete("/api/me/photo", headers=supervisor)
    assert s3.objects == {}

# Request bodies here hold passwords: never log them.

import secrets

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.auth import issue_tokens, locked_error, record_failed_login
from app.api.deps import get_current_user, get_db
from app.api.schemas import INVALID_REQUEST, NOT_LOGGED_IN, MeOut, TokenOut, error_responses
from app.core import clock, storage
from app.core.errors import ApiError
from app.core.phone import normalise_phone
from app.core.security import hash_password, verify_password
from app.models import RefreshToken, User

router = APIRouter(prefix="/api", tags=["me"])

MIN_PASSWORD_LENGTH = 8
MAX_PHOTO_BYTES = 2 * 1024 * 1024
PHOTO_FOLDER = "profile-photos"


class MeUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = None


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)
    confirm_password: str = Field(max_length=128)


@router.get("/me", response_model=MeOut, responses=error_responses(NOT_LOGGED_IN))
def me(user: User = Depends(get_current_user)):
    return user


@router.patch(
    "/me",
    response_model=MeOut,
    responses=error_responses(
        {
            **NOT_LOGGED_IN,
            409: "`conflict`: another user already has this phone number.",
            **INVALID_REQUEST,
        }
    ),
)
def update_me(
    body: MeUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fields = body.model_fields_set
    if "name" in fields:
        name = (body.name or "").strip()
        if not name:
            raise ApiError(422, "validation_error", "name: can't be empty.")
        user.name = name
    if "phone" in fields:
        if not body.phone or not body.phone.strip():
            user.phone = None
        else:
            phone = normalise_phone(body.phone)
            if phone is None:
                raise ApiError(
                    422, "validation_error", "phone: not a Ghana phone number (e.g. 0241234567)."
                )
            taken = db.scalar(select(User).where(User.phone == phone, User.id != user.id))
            if taken:
                raise ApiError(409, "conflict", "Another user already has this phone number.")
            user.phone = phone
    db.commit()
    return user


@router.post(
    "/me/password",
    response_model=TokenOut,
    responses=error_responses(
        {
            400: "`wrong_password`: the current password is wrong.",
            **NOT_LOGGED_IN,
            423: "`account_locked`: too many wrong passwords. The message says when to try again.",
            **INVALID_REQUEST,
        }
    ),
)
def change_password(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.locked_until is not None and user.locked_until > clock.now():
        raise locked_error(user.locked_until)
    if not verify_password(body.current_password, user.password_hash):
        # Counts like a failed login, so a stolen token can't be used to guess the password.
        record_failed_login(user)
        db.commit()
        if user.locked_until is not None and user.locked_until > clock.now():
            raise locked_error(user.locked_until)
        raise ApiError(400, "wrong_password", "The current password is wrong.")
    if len(body.new_password) < MIN_PASSWORD_LENGTH:
        raise ApiError(
            422,
            "validation_error",
            f"new_password: must be at least {MIN_PASSWORD_LENGTH} characters.",
        )
    if body.new_password != body.confirm_password:
        raise ApiError(422, "validation_error", "confirm_password: the passwords are not the same.")

    user.password_hash = hash_password(body.new_password)
    user.failed_login_count = 0
    user.first_failed_login_at = None
    # Logs out every other device. This device gets new tokens in the response.
    # The old tokens are deleted, not revoked: a revoked token coming back looks stolen and
    # would end the new session too (see refresh in auth.py).
    db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    tokens, _ = issue_tokens(db, user, request, response)
    db.commit()
    return tokens


def photo_type(data: bytes) -> tuple[str, str] | None:
    """(extension, content type) from the file's first bytes, or None if not JPEG/PNG/WebP."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


@router.put(
    "/me/photo",
    response_model=MeOut,
    responses=error_responses({**NOT_LOGGED_IN, **INVALID_REQUEST}),
)
def upload_photo(
    photo: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = photo.file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise ApiError(422, "validation_error", "photo: the file is bigger than 2 MB.")
    kind = photo_type(data)
    if kind is None:
        raise ApiError(422, "validation_error", "photo: must be a JPEG, PNG or WebP image.")
    extension, content_type = kind

    # A new random name each time, so browsers never show an old cached photo.
    key = f"{PHOTO_FOLDER}/{user.id}-{secrets.token_urlsafe(8)}.{extension}"
    storage.save(key, data, content_type)
    old_key = user.photo_key
    user.photo_key = key
    db.commit()
    if old_key:
        storage.delete(old_key)
    return user


@router.delete("/me/photo", response_model=MeOut, responses=error_responses(NOT_LOGGED_IN))
def delete_photo(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    old_key = user.photo_key
    user.photo_key = None
    db.commit()
    if old_key:
        storage.delete(old_key)
    return user

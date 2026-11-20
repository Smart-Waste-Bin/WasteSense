# Request bodies here hold passwords and tokens: never log them.

import math
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.schemas import INVALID_REQUEST, NOT_LOGGED_IN, TokenOut, UserOut, error_responses
from app.config import settings
from app.core import clock
from app.core.errors import ApiError
from app.core.phone import normalise_phone
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token, hash_refresh_token, new_refresh_token
from app.models import RefreshToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/auth"

# Checked when the login doesn't exist, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))

INVALID_CREDENTIALS = ApiError(401, "invalid_credentials", "Wrong email/phone or password")
INVALID_REFRESH = ApiError(401, "invalid_refresh_token", "Your session has ended. Log in again.")
ACCOUNT_DISABLED = ApiError(403, "account_disabled", "This account has been deactivated.")


class LoginIn(BaseModel):
    login: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str | None = None


class LogoutIn(BaseModel):
    refresh_token: str | None = None
    all_devices: bool = False


def find_user(db: Session, login: str) -> User | None:
    login = login.strip()
    if "@" in login:
        return db.scalar(select(User).where(User.email == login.lower()))
    phone = normalise_phone(login)
    if phone is None:
        return None
    return db.scalar(select(User).where(User.phone == phone))


def locked_error(locked_until: datetime) -> ApiError:
    minutes = max(1, math.ceil((locked_until - clock.now()).total_seconds() / 60))
    return ApiError(
        423,
        "account_locked",
        f"Too many failed logins. Try again after {locked_until:%H:%M} UTC "
        f"(in {minutes} minute{'s' if minutes != 1 else ''}).",
    )


def record_failed_login(user: User) -> None:
    now = clock.now()
    window = timedelta(minutes=settings.lockout_window_min)
    if user.first_failed_login_at is None or now - user.first_failed_login_at > window:
        user.first_failed_login_at = now
        user.failed_login_count = 1
    else:
        user.failed_login_count += 1
    if user.failed_login_count >= settings.lockout_max_attempts:
        user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
        user.failed_login_count = 0
        user.first_failed_login_at = None


def revoke_all(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=clock.now())
    )


def issue_tokens(
    db: Session, user: User, request: Request, response: Response
) -> tuple[TokenOut, uuid.UUID]:
    """New access + refresh token. Adds the refresh token row (caller commits) and sets the cookie.

    Returns the response body and the id of the new refresh token row.
    """
    access_token, expires_in = create_access_token(user.id, user.role)
    refresh_token, token_hash = new_refresh_token()
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        created_at=clock.now(),
        expires_at=clock.now() + timedelta(days=settings.refresh_token_days),
        user_agent=(request.headers.get("user-agent") or "")[:300] or None,
    )
    db.add(row)
    response.set_cookie(
        COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_days * 24 * 3600,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    body = TokenOut(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )
    return body, row.id


@router.post(
    "/login",
    response_model=TokenOut,
    responses=error_responses(
        {
            401: "`invalid_credentials`: wrong email/phone or password.",
            403: "`account_disabled`: the account has been deactivated.",
            423: "`account_locked`: too many failed logins. The message says when to try again.",
            **INVALID_REQUEST,
        }
    ),
)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = find_user(db, body.login)
    if user is None:
        verify_password(body.password, DUMMY_HASH)
        raise INVALID_CREDENTIALS

    if user.locked_until is not None and user.locked_until > clock.now():
        raise locked_error(user.locked_until)

    if not verify_password(body.password, user.password_hash):
        record_failed_login(user)
        db.commit()
        if user.locked_until is not None and user.locked_until > clock.now():
            raise locked_error(user.locked_until)
        raise INVALID_CREDENTIALS

    if not user.is_active:
        raise ACCOUNT_DISABLED

    user.failed_login_count = 0
    user.first_failed_login_at = None
    user.locked_until = None
    tokens, _ = issue_tokens(db, user, request, response)
    db.commit()
    return tokens


@router.post(
    "/refresh",
    response_model=TokenOut,
    responses=error_responses(
        {
            401: "`invalid_refresh_token`: the session has ended. Log in again.",
            403: "`account_disabled`: the account has been deactivated.",
            **INVALID_REQUEST,
        }
    ),
)
def refresh(
    request: Request,
    response: Response,
    body: RefreshIn | None = None,
    cookie_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
):
    token = (body.refresh_token if body else None) or cookie_token
    if not token:
        raise INVALID_REFRESH
    token_hash = hash_refresh_token(token)
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None:
        raise INVALID_REFRESH
    if row.revoked_at is not None:
        # A used or revoked token came back: it may be stolen. End every session of this user.
        revoke_all(db, row.user_id)
        db.commit()
        raise INVALID_REFRESH
    if row.expires_at <= clock.now():
        raise INVALID_REFRESH

    user = db.get(User, row.user_id)
    if user is None:
        raise INVALID_REFRESH
    if not user.is_active:
        raise ACCOUNT_DISABLED

    tokens, new_id = issue_tokens(db, user, request, response)
    row.revoked_at = clock.now()
    row.replaced_by = new_id
    db.commit()
    return tokens


@router.post(
    "/logout",
    status_code=204,
    responses=error_responses({**NOT_LOGGED_IN, **INVALID_REQUEST}),
)
def logout(
    body: LogoutIn | None = None,
    cookie_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body and body.all_devices:
        revoke_all(db, user.id)
    else:
        token = (body.refresh_token if body else None) or cookie_token
        if token:
            db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.token_hash == hash_refresh_token(token),
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=clock.now())
            )
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_NAME, path=COOKIE_PATH, httponly=True, samesite="lax", secure=settings.cookie_secure
    )
    return response

import hashlib
import secrets
import uuid
from datetime import timedelta

import jwt

from app.config import settings
from app.core import clock
from app.core.errors import ApiError

ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    """Return (token, expires_in seconds)."""
    issued = clock.now()
    lifetime = timedelta(minutes=settings.access_token_minutes)
    claims = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(issued.timestamp()),
        "exp": int((issued + lifetime).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    try:
        # Expiry is checked below against our clock, so tests can use a fake clock.
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_exp": False, "require": ["sub", "type", "exp"]},
        )
    except jwt.PyJWTError:
        raise ApiError(401, "invalid_token", "The login token is not valid. Log in again.")
    if claims.get("type") != "access":
        raise ApiError(401, "invalid_token", "The login token is not valid. Log in again.")
    if clock.now().timestamp() >= claims["exp"]:
        message = "The login token has expired. Refresh it or log in again."
        raise ApiError(401, "token_expired", message)
    return claims


def new_refresh_token() -> tuple[str, str]:
    """Return (token to give the client, hash to store)."""
    token = secrets.token_urlsafe(48)
    return token, hash_refresh_token(token)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

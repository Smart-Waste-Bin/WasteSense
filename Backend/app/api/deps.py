import uuid
from collections.abc import Callable, Iterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.tokens import decode_access_token
from app.db import SessionLocal
from app.models import Route, User
from app.models.enums import UserRole

bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise ApiError(401, "unauthorized", "Log in first: no login token was sent.")
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(claims["sub"])
    except ValueError:
        raise ApiError(401, "invalid_token", "The login token is not valid. Log in again.")
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(401, "invalid_token", "The login token is not valid. Log in again.")
    if not user.is_active:
        raise ApiError(403, "account_disabled", "This account has been deactivated.")
    return user


def require_role(*roles: str) -> Callable[..., User]:
    allowed = {UserRole(role) for role in roles}

    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise ApiError(403, "forbidden", "Your role is not allowed to do this.")
        return user

    return check


def ensure_own_route_or_staff(user: User, route: Route) -> None:
    if user.role == UserRole.COLLECTOR and route.collector_id != user.id:
        raise ApiError(403, "forbidden", "This route belongs to another collector.")

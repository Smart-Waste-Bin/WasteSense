import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer

from app.core import storage


def utc_z(value: datetime) -> str:
    """Contract rule: times are UTC ISO 8601 ending in Z."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: str | None
    role: str


class MeOut(UserOut):
    is_active: bool
    created_at: datetime
    photo_key: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def photo_url(self) -> str | None:
        return storage.url(self.photo_key)

    @field_serializer("created_at")
    def created_at_utc(self, value: datetime) -> str:
        return utc_z(value)


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user: UserOut


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorOut(BaseModel):
    """Every error the API sends has this shape (see app/core/errors.py)."""

    error: ErrorBody


def error_responses(errors: dict[int, str]) -> dict:
    """For the API docs: the error codes a route can answer with, per HTTP status."""
    return {status: {"model": ErrorOut, "description": text} for status, text in errors.items()}


INVALID_REQUEST = {422: "`validation_error`: a field is missing or has the wrong format."}
NOT_LOGGED_IN = {
    401: "`unauthorized`, `invalid_token` or `token_expired`: log in (again).",
    403: "`account_disabled`: the account has been deactivated.",
}

"""BE-08: record a bin as emptied, and the collection history (contract v1.6)."""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.bin_schemas import Number, number
from app.api.bins import NOT_FOUND, STAFF_ONLY, get_live_bin_or_404
from app.api.deps import ensure_own_route_or_staff, get_current_user, get_db, require_role
from app.api.schemas import INVALID_REQUEST, NOT_LOGGED_IN, error_responses, utc_z
from app.collections.service import record_collection, route_id_of
from app.core import clock
from app.core.errors import ApiError
from app.models import Collection, Route, RouteStop, User

router = APIRouter(prefix="/api/collections", tags=["collections"])

OTHER_ROUTE = {403: "`forbidden`: the stop is on another collector's route."}
CONFLICT = {409: "`conflict`: this idempotency_key was already used for another bin."}


class CollectionIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "bin_id": "BIN-002",
                "idempotency_key": "0f8e6a52-3c1b-4d7e-9a24-6b5c8d1e2f30",
                "stop_id": "c41e8b07-2d9a-4f63-8e15-9b0a7c2d4e66",
                "emptied_at": "2026-11-07T09:10:00Z",
            }
        },
    )

    bin_id: str
    # Made once by the app per "emptied" tap and sent again on every retry.
    idempotency_key: uuid.UUID
    stop_id: uuid.UUID | None = None  # null when emptied outside a route
    emptied_at: datetime | None = None  # default: now


class CollectionOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "5d2b7c9e-1a3f-4e86-b0d4-7f9a2c6e1b38",
                "bin_id": "BIN-002",
                "collector_id": "3b8d1f4a-6c2e-4a97-b5d0-8e1f2a3c4d55",
                "stop_id": "c41e8b07-2d9a-4f63-8e15-9b0a7c2d4e66",
                "route_id": "7f3c9a2e-4b1d-4e8a-9c2f-1a6b5d3e8f01",
                "emptied_at": "2026-11-07T09:10:00Z",
                "fill_before": 92,
                "confirmation": "confirmed",
                "confirmed_by_sensor": True,
                "confirmed_at": "2026-11-07T09:15:02Z",
                "unconfirmed_at": None,
                "created_at": "2026-11-07T09:10:01Z",
            }
        }
    )

    id: uuid.UUID
    bin_id: str
    collector_id: uuid.UUID
    stop_id: uuid.UUID | None
    route_id: uuid.UUID | None
    emptied_at: datetime
    fill_before: Number | None
    confirmation: str  # waiting, confirmed or unconfirmed
    confirmed_by_sensor: bool
    confirmed_at: datetime | None
    unconfirmed_at: datetime | None
    created_at: datetime

    @field_serializer("emptied_at", "confirmed_at", "unconfirmed_at", "created_at")
    def times_utc(self, value: datetime | None) -> str | None:
        return utc_z(value) if value else None


class CollectionsPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [CollectionOut.model_config["json_schema_extra"]["example"]],
                "total": 1,
            }
        }
    )

    items: list[CollectionOut]
    total: int


def confirmation(collection: Collection) -> str:
    if collection.confirmed_by_sensor:
        return "confirmed"
    return "unconfirmed" if collection.unconfirmed_at else "waiting"


def collection_out(db: Session, collection: Collection) -> CollectionOut:
    return CollectionOut(
        id=collection.id,
        bin_id=collection.bin_id,
        collector_id=collection.collector_id,
        stop_id=collection.stop_id,
        route_id=route_id_of(db, collection),
        emptied_at=collection.emptied_at,
        fill_before=number(collection.fill_before),
        confirmation=confirmation(collection),
        confirmed_by_sensor=collection.confirmed_by_sensor,
        confirmed_at=collection.confirmed_at,
        unconfirmed_at=collection.unconfirmed_at,
        created_at=collection.created_at,
    )


@router.post(
    "",
    status_code=201,
    response_model=CollectionOut,
    responses={200: {"description": "Sent before: the first collection, unchanged"}}
    | error_responses(NOT_LOGGED_IN | OTHER_ROUTE | NOT_FOUND | CONFLICT | INVALID_REQUEST),
)
def create_collection(
    body: CollectionIn,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """A bin was emptied. Saves one collection and sends `bins/{id}/emptied` over MQTT.

    Safe to retry: the same `idempotency_key` (or the same stop) returns the first collection
    with `200` instead of making a second one. The sensor then confirms it (contract v1.6).
    """
    the_bin = get_live_bin_or_404(db, body.bin_id)
    now = clock.now()
    emptied_at = body.emptied_at or now
    if emptied_at > now + timedelta(minutes=1):
        raise ApiError(422, "validation_error", "emptied_at can't be in the future.")

    stop = None
    if body.stop_id is not None:
        stop = db.get(RouteStop, body.stop_id)
        if stop is None:
            raise ApiError(404, "not_found", "No route stop with this ID.")
        if stop.bin_id != the_bin.id:
            raise ApiError(422, "validation_error", "stop_id is a stop for another bin.")
        ensure_own_route_or_staff(user, db.get(Route, stop.route_id))

    collection, created = record_collection(
        db,
        the_bin=the_bin,
        collector_id=user.id,
        emptied_at=emptied_at,
        idempotency_key=body.idempotency_key,
        stop=stop,
    )
    if not created:
        response.status_code = 200
    return collection_out(db, collection)


@router.get(
    "",
    response_model=CollectionsPage,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | INVALID_REQUEST),
)
def list_collections(
    bin_id: str | None = Query(None),
    confirmation_: str | None = Query(
        None, alias="confirmation", pattern="^(waiting|confirmed|unconfirmed)$"
    ),
    from_: datetime | None = Query(None, alias="from", description="emptied_at from (included)"),
    to: datetime | None = Query(None, description="emptied_at before (not included)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Collection history, newest first."""
    query = select(Collection)
    if bin_id:
        query = query.where(Collection.bin_id == bin_id)
    if confirmation_ == "confirmed":
        query = query.where(Collection.confirmed_by_sensor.is_(True))
    elif confirmation_ == "unconfirmed":
        query = query.where(
            Collection.confirmed_by_sensor.is_(False), Collection.unconfirmed_at.is_not(None)
        )
    elif confirmation_ == "waiting":
        query = query.where(
            Collection.confirmed_by_sensor.is_(False), Collection.unconfirmed_at.is_(None)
        )
    if from_:
        query = query.where(Collection.emptied_at >= from_)
    if to:
        query = query.where(Collection.emptied_at < to)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Collection.emptied_at.desc(), Collection.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return CollectionsPage(items=[collection_out(db, row) for row in rows], total=total)

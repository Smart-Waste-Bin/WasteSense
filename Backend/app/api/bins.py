"""BE-04: bins and readings API. Contract sections 5 and 6."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.bin_schemas import (
    BinCreate,
    BinOut,
    BinsPage,
    BinUpdate,
    HourReadingOut,
    Location,
    RawReadingOut,
    ReadingsPage,
    number,
)
from app.api.deps import get_current_user, get_db, require_role
from app.api.schemas import INVALID_REQUEST, NOT_LOGGED_IN, error_responses
from app.core import clock, events
from app.core.errors import ApiError
from app.models import Bin, Reading, User
from app.models.enums import BinStatus
from app.status.engine import bin_updated_data, refresh_bin

router = APIRouter(prefix="/api/bins", tags=["bins"])

STAFF_ONLY = {403: "`forbidden`: only admin and supervisor may do this."}
NOT_FOUND = {404: "`not_found`: no bin with this ID, or it is deleted."}
CONFLICT = {409: "`conflict`: the bin ID or sensor ID is already used."}

SORT_FIELDS = {
    "id": Bin.id,
    "name": Bin.name,
    "status": Bin.status,
    "last_fill": Bin.last_fill,
    "last_battery": Bin.last_battery,
    "last_seen_at": Bin.last_seen_at,
    "created_at": Bin.created_at,
}

GEOM = cast(Bin.location, Geometry)
LAT = func.ST_Y(GEOM).label("lat")
LNG = func.ST_X(GEOM).label("lng")


def point(lat: float, lng: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


def bin_out(the_bin: Bin, lat: float, lng: float) -> BinOut:
    return BinOut(
        id=the_bin.id,
        name=the_bin.name,
        location=Location(lat=lat, lng=lng),
        depth_cm=number(the_bin.depth_cm),
        volume_l=number(the_bin.volume_l),
        sensor_id=the_bin.sensor_id,
        status=the_bin.status,
        maintenance=the_bin.maintenance,
        is_physical=the_bin.is_physical,
        due_threshold=number(the_bin.due_threshold),
        urgent_threshold=number(the_bin.urgent_threshold),
        last_fill=number(the_bin.last_fill),
        last_battery=number(the_bin.last_battery),
        last_seen_at=the_bin.last_seen_at,
        created_at=the_bin.created_at,
    )


def get_live_bin_or_404(db: Session, bin_id: str) -> Bin:
    the_bin = db.get(Bin, bin_id)
    if the_bin is None or the_bin.deleted_at is not None:
        raise ApiError(404, "not_found", f"Bin {bin_id} was not found.")
    return the_bin


def load_bin_out(db: Session, bin_id: str) -> BinOut:
    row = db.execute(select(Bin, LAT, LNG).where(Bin.id == bin_id)).one()
    return bin_out(row.Bin, row.lat, row.lng)


def next_bin_id(db: Session) -> str:
    """The next free BIN-NNN, counting deleted bins too (their IDs are never reused)."""
    ids = db.scalars(select(Bin.id)).all()
    highest = max((int(bin_id.split("-")[1]) for bin_id in ids), default=0)
    return f"BIN-{highest + 1:03d}"


def check_thresholds(the_bin: Bin) -> None:
    due, urgent = the_bin.due_threshold, the_bin.urgent_threshold
    if due is not None and urgent is not None and due >= urgent:
        raise ApiError(422, "validation_error", "due_threshold must be below urgent_threshold.")


# --- Bins ---


@router.get("", response_model=BinsPage, responses=error_responses(NOT_LOGGED_IN | INVALID_REQUEST))
def list_bins(
    status: str | None = Query(None, description="One or more statuses, e.g. `due,urgent`"),
    q: str | None = Query(None, description="Search in the bin ID and name"),
    is_physical: bool | None = Query(None),
    sort: str = Query("id", description="A field name. Leading `-` = largest first."),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Bin, LAT, LNG).where(Bin.deleted_at.is_(None))

    if status:
        wanted = [value.strip() for value in status.split(",") if value.strip()]
        allowed = {item.value for item in BinStatus}
        bad = [value for value in wanted if value not in allowed]
        if bad:
            raise ApiError(
                422, "validation_error", f"status: unknown value {bad[0]}. Use {sorted(allowed)}."
            )
        query = query.where(Bin.status.in_(wanted))
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Bin.id.ilike(pattern), Bin.name.ilike(pattern)))
    if is_physical is not None:
        query = query.where(Bin.is_physical.is_(is_physical))

    field = sort.removeprefix("-")
    if field not in SORT_FIELDS:
        raise ApiError(422, "validation_error", f"sort: use one of {sorted(SORT_FIELDS)}.")
    column = SORT_FIELDS[field]
    order = column.desc().nulls_last() if sort.startswith("-") else column.asc().nulls_last()

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.order_by(order, Bin.id).offset((page - 1) * size).limit(size)).all()
    return BinsPage(items=[bin_out(row.Bin, row.lat, row.lng) for row in rows], total=total)


@router.post(
    "",
    status_code=201,
    response_model=BinOut,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | CONFLICT | INVALID_REQUEST),
)
def create_bin(
    body: BinCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    bin_id = body.id or next_bin_id(db)
    if db.get(Bin, bin_id) is not None:
        raise ApiError(409, "conflict", f"Bin ID {bin_id} is already used.")

    the_bin = Bin(
        id=bin_id,
        name=body.name,
        location=point(body.location.lat, body.location.lng),
        depth_cm=body.depth_cm,
        volume_l=body.volume_l,
        sensor_id=body.sensor_id,
        is_physical=body.is_physical,
        due_threshold=body.due_threshold,
        urgent_threshold=body.urgent_threshold,
        maintenance=False,
    )
    check_thresholds(the_bin)
    refresh_bin(db, the_bin, clock.now())  # a new bin has never reported, so it starts Offline
    db.add(the_bin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "conflict", "That sensor ID is already used by another bin.")
    return load_bin_out(db, bin_id)


@router.get(
    "/{bin_id}", response_model=BinOut, responses=error_responses(NOT_LOGGED_IN | NOT_FOUND)
)
def get_bin(bin_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_live_bin_or_404(db, bin_id)
    return load_bin_out(db, bin_id)


@router.patch(
    "/{bin_id}",
    response_model=BinOut,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | NOT_FOUND | CONFLICT | INVALID_REQUEST),
)
def update_bin(
    bin_id: str,
    body: BinUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    the_bin = get_live_bin_or_404(db, bin_id)
    changes = body.model_dump(exclude_unset=True)

    for field in ("name", "depth_cm", "volume_l", "maintenance", "is_physical"):
        if field in changes and changes[field] is None:
            raise ApiError(422, "validation_error", f"{field}: may not be null.")
    if "location" in changes:
        if body.location is None:
            raise ApiError(422, "validation_error", "location: may not be null.")
        the_bin.location = point(body.location.lat, body.location.lng)
        del changes["location"]
    for field, value in changes.items():
        setattr(the_bin, field, value)
    check_thresholds(the_bin)

    # Maintenance or a threshold may change the status (BE-03).
    status_changed = refresh_bin(db, the_bin, clock.now())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "conflict", "That sensor ID is already used by another bin.")
    if status_changed:
        events.emit("bin_updated", bin_updated_data(the_bin))
    return load_bin_out(db, bin_id)


@router.delete(
    "/{bin_id}",
    status_code=204,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | NOT_FOUND),
)
def delete_bin(
    bin_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Soft delete: the bin disappears from the API, its readings are kept."""
    the_bin = get_live_bin_or_404(db, bin_id)
    the_bin.deleted_at = clock.now()
    db.commit()
    return Response(status_code=204)


# --- Readings ---


@router.get(
    "/{bin_id}/readings",
    response_model=ReadingsPage,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | NOT_FOUND | INVALID_REQUEST),
)
def list_readings(
    bin_id: str,
    from_: datetime | None = Query(None, alias="from", description="Default: 24 h before `to`"),
    to: datetime | None = Query(None, description="Default: now"),
    bucket: str = Query("raw", pattern="^(raw|hour)$", description="`raw` or `hour`"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=1000, description="Up to 1000, so 30 days of hours fit"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Oldest first. `hour` = average and max fill per hour (UTC), worked out in SQL."""
    get_live_bin_or_404(db, bin_id)
    end = to or clock.now()
    start = from_ or end - timedelta(hours=24)
    if start >= end:
        raise ApiError(422, "validation_error", "from must be before to.")

    in_range = (Reading.bin_id == bin_id, Reading.device_ts >= start, Reading.device_ts < end)
    offset = (page - 1) * size

    if bucket == "raw":
        query = select(Reading).where(*in_range)
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        readings = db.scalars(query.order_by(Reading.device_ts).offset(offset).limit(size)).all()
        raw_items = [
            RawReadingOut(
                seq=row.seq,
                fill=number(row.fill),
                distance_cm=number(row.distance_cm),
                battery=number(row.battery),
                rssi=row.rssi,
                ts=row.device_ts,
                received_at=row.received_at,
                is_late=row.is_late,
            )
            for row in readings
        ]
        return ReadingsPage(items=raw_items, total=total)

    hour = func.date_trunc("hour", Reading.device_ts, "UTC").label("hour")
    hours = (
        select(
            hour,
            func.avg(Reading.fill).label("avg_fill"),
            func.max(Reading.fill).label("max_fill"),
            func.count().label("reading_count"),
        )
        .where(*in_range)
        .group_by(hour)
    )
    total = db.scalar(select(func.count()).select_from(hours.subquery())) or 0
    rows = db.execute(hours.order_by(hour).offset(offset).limit(size)).all()
    hour_items = [
        HourReadingOut(
            ts=row.hour,
            avg_fill=round(float(row.avg_fill), 1),
            max_fill=number(row.max_fill),
            count=row.reading_count,
        )
        for row in rows
    ]
    return ReadingsPage(items=hour_items, total=total)

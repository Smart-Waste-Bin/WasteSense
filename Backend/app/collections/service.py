"""BE-08: collection records and sensor confirmation (ticket SB-20, contract v1.6).

- record_collection: a bin was emptied. One collection row, and bins/{id}/emptied over MQTT.
- confirm_with_reading: called for every stored reading. Confirms the bin's open collections.
- flag_unconfirmed: run every 60 s. Flags collections not confirmed after 30 minutes and
  notifies the supervisors.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import utc_z
from app.core import events
from app.core.errors import ApiError
from app.models import Bin, Collection, Notification, RouteStop, User
from app.models.enums import StopStatus, UserRole

CONFIRM_WITHIN = timedelta(minutes=30)
CONFIRM_BELOW = 20  # fill under 20 % ...
CONFIRM_DROP = 40  # ... or a drop of 40 points or more


def route_id_of(session: Session, collection: Collection) -> uuid.UUID | None:
    if collection.stop_id is None:
        return None
    stop = session.get(RouteStop, collection.stop_id)
    return stop.route_id if stop else None


def record_collection(
    session: Session,
    *,
    the_bin: Bin,
    collector_id: uuid.UUID,
    emptied_at: datetime,
    idempotency_key: uuid.UUID,
    stop: RouteStop | None = None,
) -> tuple[Collection, bool]:
    """Returns (collection, created). Sending the same request again (same idempotency_key,
    or the same stop) gives back the first collection instead of making a second one."""
    existing = session.scalar(
        select(Collection).where(Collection.idempotency_key == idempotency_key)
    )
    if existing is None and stop is not None:
        existing = session.scalar(select(Collection).where(Collection.stop_id == stop.id))
    if existing is not None:
        if existing.bin_id != the_bin.id:
            raise ApiError(409, "conflict", "This idempotency_key was used for another bin.")
        return existing, False

    collection = Collection(
        bin_id=the_bin.id,
        collector_id=collector_id,
        stop_id=stop.id if stop else None,
        emptied_at=emptied_at,
        fill_before=the_bin.last_fill,
        idempotency_key=idempotency_key,
    )
    session.add(collection)
    if stop is not None:
        stop.status = StopStatus.EMPTIED.value
        stop.emptied_at = emptied_at
    try:
        session.commit()
    except IntegrityError:
        # Two copies of the same request at the same moment: the other one won.
        session.rollback()
        existing = session.scalar(
            select(Collection).where(Collection.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        return existing, False

    from app.ingest import mqtt_client  # here, not at the top: mqtt_client imports ingest

    route_id = route_id_of(session, collection)
    mqtt_client.publish_emptied(
        {
            "bin_id": the_bin.id,
            "emptied_at": utc_z(emptied_at),
            "route_id": str(route_id) if route_id else None,
        }
    )
    return collection, True


def shows_emptied(fill: Decimal | float, fill_before: Decimal | None) -> bool:
    if fill < CONFIRM_BELOW:
        return True
    return fill_before is not None and fill_before - Decimal(str(fill)) >= CONFIRM_DROP


def confirm_with_reading(
    session: Session, bin_id: str, fill: float, taken_at: datetime, now: datetime
) -> list[uuid.UUID]:
    """Confirm the bin's collections that this reading proves. The caller commits.

    The reading must be taken after the emptying and within 30 minutes of it. A collection
    that was already flagged can still be confirmed by a late reading: the proof is real.
    """
    open_ones = session.scalars(
        select(Collection).where(
            Collection.bin_id == bin_id,
            Collection.confirmed_by_sensor.is_(False),
            Collection.emptied_at <= taken_at,
            Collection.emptied_at >= taken_at - CONFIRM_WITHIN,
        )
    ).all()
    confirmed = []
    for collection in open_ones:
        if shows_emptied(fill, collection.fill_before):
            collection.confirmed_by_sensor = True
            collection.confirmed_at = now
            confirmed.append(collection.id)
    return confirmed


def notification_data(note: Notification) -> dict[str, Any]:
    """Same shape as an item of GET /api/notifications (contract), plus user_id so the
    WebSocket hub knows who it is for (it strips user_id before sending)."""
    return {
        "id": note.id,
        "type": note.type,
        "title": note.title,
        "body": note.body,
        "data": note.data,
        "is_read": note.is_read,
        "created_at": utc_z(note.created_at),
        "user_id": str(note.user_id),
    }


def flag_unconfirmed(session: Session, now: datetime) -> list[uuid.UUID]:
    """Flag collections still unconfirmed 30 minutes after emptying, and notify every active
    supervisor once per collection."""
    overdue = session.scalars(
        select(Collection).where(
            Collection.confirmed_by_sensor.is_(False),
            Collection.unconfirmed_at.is_(None),
            Collection.emptied_at < now - CONFIRM_WITHIN,
        )
    ).all()
    if not overdue:
        return []

    supervisors = session.scalars(
        select(User).where(User.role == UserRole.SUPERVISOR.value, User.is_active.is_(True))
    ).all()
    notes = []
    for collection in overdue:
        collection.unconfirmed_at = now
        the_bin = session.get(Bin, collection.bin_id)
        fill = "no reading yet" if the_bin.last_fill is None else f"{the_bin.last_fill}% full"
        for supervisor in supervisors:
            note = Notification(
                user_id=supervisor.id,
                type="collection_unconfirmed",
                title="Collection not confirmed",
                body=(
                    f"{collection.bin_id} was marked emptied at "
                    f"{collection.emptied_at:%H:%M} UTC, but its sensor still shows {fill}."
                ),
                data={"collection_id": str(collection.id), "bin_id": collection.bin_id},
                created_at=now,
            )
            session.add(note)
            notes.append(note)
    session.commit()
    for note in notes:
        events.emit("notification", notification_data(note))
    return [collection.id for collection in overdue]

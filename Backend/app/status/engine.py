"""BE-03: keeps every bin's status up to date.

compute_status() holds the rules. refresh_bin() applies them to one bin after a reading.
mark_offline_bins() runs every 60 s and catches bins that stopped reporting.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import events
from app.models import Bin, Setting
from app.models.enums import BinStatus

FILLING_FROM = 50

DEFAULTS = {"due_threshold": 70, "urgent_threshold": 90, "offline_timeout_min": 15}


@dataclass
class StatusSettings:
    due_threshold: float
    urgent_threshold: float
    offline_timeout_min: float


def compute_status(
    last_fill: float | None,
    last_seen_at: datetime | None,
    maintenance: bool,
    settings: StatusSettings,
    now: datetime,
) -> BinStatus:
    """The rules, first match wins."""
    if maintenance:
        return BinStatus.MAINTENANCE
    # Never reported, or quiet for too long.
    if last_seen_at is None or last_fill is None:
        return BinStatus.OFFLINE
    if now - last_seen_at > timedelta(minutes=settings.offline_timeout_min):
        return BinStatus.OFFLINE
    if last_fill >= settings.urgent_threshold:
        return BinStatus.URGENT
    if last_fill >= settings.due_threshold:
        return BinStatus.DUE
    if last_fill >= FILLING_FROM:
        return BinStatus.FILLING
    return BinStatus.NORMAL


def load_global_settings(session: Session) -> dict[str, float]:
    rows = session.scalars(select(Setting).where(Setting.key.in_(DEFAULTS.keys())))
    values = {key: float(value) for key, value in DEFAULTS.items()}
    for row in rows:
        values[row.key] = float(row.value)
    return values


def settings_for(the_bin: Bin, global_settings: dict[str, float]) -> StatusSettings:
    """A bin's own thresholds win over the global ones (NULL means use the global value)."""
    due = the_bin.due_threshold
    urgent = the_bin.urgent_threshold
    return StatusSettings(
        due_threshold=float(due) if due is not None else global_settings["due_threshold"],
        urgent_threshold=float(urgent)
        if urgent is not None
        else global_settings["urgent_threshold"],
        offline_timeout_min=global_settings["offline_timeout_min"],
    )


def bin_updated_data(the_bin: Bin) -> dict[str, Any]:
    """The data part of the bin_updated event (Docs/contract/examples/ws/bin_updated.json)."""

    def number(value: Decimal | None) -> int | float | None:
        if value is None:
            return None
        return int(value) if value == int(value) else float(value)

    seen = the_bin.last_seen_at
    return {
        "id": the_bin.id,
        "status": the_bin.status,
        "last_fill": number(the_bin.last_fill),
        "last_battery": number(the_bin.last_battery),
        "last_seen_at": seen.strftime("%Y-%m-%dT%H:%M:%SZ") if seen else None,
    }


def refresh_bin(session: Session, the_bin: Bin, now: datetime) -> bool:
    """Recalculate one bin's status. Returns True if it changed. The caller commits."""
    settings = settings_for(the_bin, load_global_settings(session))
    new_status = compute_status(
        float(the_bin.last_fill) if the_bin.last_fill is not None else None,
        the_bin.last_seen_at,
        the_bin.maintenance,
        settings,
        now,
    )
    if the_bin.status == new_status.value:
        return False
    the_bin.status = new_status.value
    return True


def mark_offline_bins(session: Session, now: datetime) -> list[str]:
    """Every 60 s: bins that stopped reporting go Offline. Returns the IDs that changed.

    Only moves bins TO offline. Coming back is handled by the next reading (refresh_bin),
    so this job never undoes an offline set by the device's last will.
    """
    global_settings = load_global_settings(session)
    bins = session.scalars(
        select(Bin).where(Bin.deleted_at.is_(None), Bin.status != BinStatus.OFFLINE.value)
    ).all()

    changed = []
    for the_bin in bins:
        settings = settings_for(the_bin, global_settings)
        new_status = compute_status(
            float(the_bin.last_fill) if the_bin.last_fill is not None else None,
            the_bin.last_seen_at,
            the_bin.maintenance,
            settings,
            now,
        )
        if new_status == BinStatus.OFFLINE:
            the_bin.status = new_status.value
            changed.append(the_bin)

    session.commit()
    for the_bin in changed:
        events.emit("bin_updated", bin_updated_data(the_bin))
    return [the_bin.id for the_bin in changed]

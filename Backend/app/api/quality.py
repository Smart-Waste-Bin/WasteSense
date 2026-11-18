"""BE-07: how complete and trustworthy a bin's data is (ticket SB-19, contract v1.5)."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.bins import NOT_FOUND, STAFF_ONLY, get_live_bin_or_404
from app.api.deps import get_db, require_role
from app.api.schemas import INVALID_REQUEST, NOT_LOGGED_IN, error_responses, utc_z
from app.core import clock
from app.core.errors import ApiError
from app.ingest.service import reporting_interval_s
from app.models import Bin, Reading, RejectedReading, User

router = APIRouter(prefix="/api/bins", tags=["data quality"])


class QualityOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "bin_id": "BIN-001",
                "from": "2026-11-06T08:30:00Z",
                "to": "2026-11-07T08:30:00Z",
                "interval_s": 300,
                "received": 279,
                "expected": 288,
                "missing": 9,
                "duplicates": 2,
                "late": 6,
                "rejected": 3,
                "rejected_by_reason": {"fill_out_of_range": 2, "bad_timestamp": 1},
            }
        },
    )

    bin_id: str
    from_: datetime = Field(alias="from")
    to: datetime
    interval_s: int
    received: int
    expected: int
    missing: int
    duplicates: int
    late: int
    rejected: int
    rejected_by_reason: dict[str, int]

    @field_serializer("from_", "to")
    def times_utc(self, value: datetime) -> str:
        return utc_z(value)


class RejectedOut(BaseModel):
    id: int
    reason: str
    received_at: datetime
    raw: Any

    @field_serializer("received_at")
    def received_utc(self, value: datetime) -> str:
        return utc_z(value)


class RejectedPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": 88,
                        "reason": "fill_out_of_range",
                        "received_at": "2026-11-07T08:30:01Z",
                        "raw": {"bin_id": "BIN-001", "fill": 120, "seq": 1043},
                    }
                ],
                "total": 1,
            }
        }
    )

    items: list[RejectedOut]
    total: int


def time_window(from_: datetime | None, to: datetime | None) -> tuple[datetime, datetime]:
    """Default: the last 24 h. The end never goes past now (nothing is expected from the future)."""
    now = clock.now()
    end = min(to, now) if to else now
    start = from_ or end - timedelta(hours=24)
    if start >= end:
        raise ApiError(422, "validation_error", "from must be before to (and before now).")
    return start, end


def rejected_query(bin_id: str, start: datetime, end: datetime):
    """Rejected messages have no trusted ts, so they are counted by when they arrived.
    They are matched on the topic, because a malformed message may have no bin_id."""
    return select(RejectedReading).where(
        RejectedReading.topic == f"bins/{bin_id}/readings",
        RejectedReading.received_at >= start,
        RejectedReading.received_at < end,
    )


@router.get(
    "/{bin_id}/quality",
    response_model=QualityOut,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | NOT_FOUND | INVALID_REQUEST),
)
def quality(
    bin_id: str,
    from_: datetime | None = Query(None, alias="from", description="Default: 24 h before `to`"),
    to: datetime | None = Query(None, description="Default: now"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Data quality for one bin over a time range (`from` included, `to` not).

    - **received**: readings stored, by when they were taken (`ts`).
    - **expected**: the time range (from when the bin was added) / `reporting_interval_s`.
      A healthy bin sends at least that many (the heartbeat); one that sends on change sends more.
    - **missing**: expected - received, never below 0.
    - **late**: stored readings flagged late. **duplicates** and **rejected**: by arrival time.
    """
    the_bin: Bin = get_live_bin_or_404(db, bin_id)
    start, end = time_window(from_, to)
    interval = reporting_interval_s(db)

    expected_from = max(start, the_bin.created_at)
    expected = max(int((end - expected_from).total_seconds() // interval), 0)

    in_range = (Reading.bin_id == bin_id, Reading.device_ts >= start, Reading.device_ts < end)
    received = db.scalar(select(func.count()).select_from(Reading).where(*in_range)) or 0
    late = (
        db.scalar(select(func.count()).select_from(Reading).where(*in_range, Reading.is_late)) or 0
    )

    rejects = rejected_query(bin_id, start, end).subquery()
    by_reason = dict(
        db.execute(select(rejects.c.reason, func.count()).group_by(rejects.c.reason)).all()
    )
    duplicates = by_reason.pop("duplicate", 0)

    return {
        "bin_id": bin_id,
        "from": start,
        "to": end,
        "interval_s": interval,
        "received": received,
        "expected": expected,
        "missing": max(expected - received, 0),
        "duplicates": duplicates,
        "late": late,
        "rejected": sum(by_reason.values()),
        "rejected_by_reason": by_reason,
    }


@router.get(
    "/{bin_id}/rejected",
    response_model=RejectedPage,
    responses=error_responses(NOT_LOGGED_IN | STAFF_ONLY | NOT_FOUND | INVALID_REQUEST),
)
def rejected(
    bin_id: str,
    from_: datetime | None = Query(None, alias="from", description="Default: 24 h before `to`"),
    to: datetime | None = Query(None, description="Default: now"),
    reason: str | None = Query(None, description="Only this reason, e.g. `fill_out_of_range`"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Messages for this bin that were not stored, newest first, with the reason.
    Duplicates are included with reason `duplicate`. For the "Rejected: reason" tags."""
    get_live_bin_or_404(db, bin_id)
    start, end = time_window(from_, to)
    query = rejected_query(bin_id, start, end)
    if reason:
        query = query.where(RejectedReading.reason == reason)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(RejectedReading.received_at.desc(), RejectedReading.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [
        RejectedOut(id=row.id, reason=row.reason, received_at=row.received_at, raw=row.raw)
        for row in rows
    ]
    return RejectedPage(items=items, total=total)

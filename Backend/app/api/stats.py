"""BE-04: the numbers on the dashboard's overview cards."""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.bin_schemas import OverviewOut, number
from app.api.deps import get_db, require_role
from app.api.schemas import NOT_LOGGED_IN, error_responses
from app.core import clock
from app.models import Bin, Collection, Route, User
from app.models.enums import BinStatus, RouteStatus

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get(
    "/overview",
    response_model=OverviewOut,
    responses=error_responses(
        NOT_LOGGED_IN | {403: "`forbidden`: only admin and supervisor may do this."}
    ),
)
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    """Days and weeks are in UTC (Ghana is UTC+0). A week starts on Monday."""
    now = clock.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=today.weekday())

    def count_bins(*conditions) -> int:
        query = select(func.count()).select_from(Bin).where(Bin.deleted_at.is_(None), *conditions)
        return db.scalar(query) or 0

    collections_today = db.scalar(
        select(func.count()).select_from(Collection).where(Collection.emptied_at >= today)
    )
    # Saved = the fixed-route baseline minus the optimised route, for routes finished this week.
    distance_saved = db.scalar(
        select(func.coalesce(func.sum(Route.baseline_fixed_m - Route.total_distance_m), 0)).where(
            Route.status == RouteStatus.COMPLETED.value,
            Route.completed_at >= week_start,
            Route.baseline_fixed_m.is_not(None),
        )
    )

    return OverviewOut(
        total_bins=count_bins(),
        needing_collection=count_bins(
            Bin.status.in_([BinStatus.DUE.value, BinStatus.URGENT.value])
        ),
        offline=count_bins(Bin.status == BinStatus.OFFLINE.value),
        collections_today=collections_today or 0,
        distance_saved_week_m=number(distance_saved) or 0,
    )

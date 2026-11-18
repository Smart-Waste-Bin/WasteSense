"""Runs the 60 s jobs while the app is up (see app/main.py): the offline check (BE-03) and
the unconfirmed-collection check (BE-08)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.collections.service import flag_unconfirmed
from app.core import clock
from app.db import SessionLocal
from app.status.engine import mark_offline_bins

log = logging.getLogger(__name__)

CHECK_EVERY_S = 60


def run_offline_check() -> None:
    try:
        with SessionLocal() as session:
            changed = mark_offline_bins(session, clock.now())
        if changed:
            log.info("Bins now offline: %s", changed)
    except Exception:
        log.exception("Offline check failed")


def run_collection_check() -> None:
    try:
        with SessionLocal() as session:
            flagged = flag_unconfirmed(session, clock.now())
        if flagged:
            log.info("Collections not confirmed after 30 min: %s", flagged)
    except Exception:
        log.exception("Collection check failed")


def start_status_job() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_offline_check, "interval", seconds=CHECK_EVERY_S, id="offline_check")
    scheduler.add_job(
        run_collection_check, "interval", seconds=CHECK_EVERY_S, id="collection_check"
    )
    scheduler.start()
    return scheduler

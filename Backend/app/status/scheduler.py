"""Runs the offline check every 60 s while the app is up (see app/main.py)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

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


def start_status_job() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_offline_check, "interval", seconds=CHECK_EVERY_S, id="offline_check")
    scheduler.start()
    return scheduler

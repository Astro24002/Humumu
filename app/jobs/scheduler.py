"""APScheduler wiring for fetch pipeline and daily summary.

Scheduler is OFF by default. Enable with env ``HUMUMU_ENABLE_SCHEDULER=1``.
This keeps ASGI/pytest lifespans from starting background jobs.
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import Settings, get_settings
from app.db import get_session_factory
from app.jobs.daily_summary import run_daily_summary
from app.jobs.fetch_pipeline import run_fetch_pipeline

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def scheduler_enabled() -> bool:
    """True only when HUMUMU_ENABLE_SCHEDULER=1 (default off for tests/safety)."""
    return os.environ.get("HUMUMU_ENABLE_SCHEDULER", "").strip() == "1"


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def start_scheduler(settings: Settings | None = None) -> AsyncIOScheduler | None:
    """
    Start AsyncIOScheduler if enabled via env.

    Jobs:
      - interval fetch every ``fetch_interval_minutes``
      - cron daily summary at 08:00 local
    """
    global _scheduler
    if not scheduler_enabled():
        logger.info(
            "scheduler not started (set HUMUMU_ENABLE_SCHEDULER=1 to enable)"
        )
        return None

    if _scheduler is not None and _scheduler.running:
        return _scheduler

    settings = settings or get_settings()
    session_factory = get_session_factory()
    if session_factory is None:
        logger.warning("scheduler: session factory not initialized; skip start")
        return None

    sched = AsyncIOScheduler()

    interval_min = max(int(settings.fetch_interval_minutes or 30), 1)

    async def _fetch_job() -> None:
        await run_fetch_pipeline(session_factory, settings)

    async def _summary_job() -> None:
        await run_daily_summary(session_factory, settings)

    sched.add_job(
        _fetch_job,
        trigger="interval",
        minutes=interval_min,
        id="fetch_pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        _summary_job,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_summary",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    logger.info(
        "scheduler started: fetch every %d min, daily summary at 08:00",
        interval_min,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler if running."""
    global _scheduler
    if _scheduler is not None:
        try:
            if _scheduler.running:
                _scheduler.shutdown(wait=False)
                logger.info("scheduler stopped")
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler shutdown error: %s", exc)
    _scheduler = None

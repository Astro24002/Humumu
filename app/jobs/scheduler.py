"""APScheduler wiring for fetch pipeline and daily summary.

Scheduler is OFF by default. Enable with env ``HUMUMU_ENABLE_SCHEDULER=1``.
This keeps ASGI/pytest lifespans from starting background jobs.
"""

from __future__ import annotations

import logging
import os
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings, get_settings
from app.db import get_session_factory
from app.jobs.daily_summary import run_daily_summary
from app.jobs.fetch_pipeline import run_fetch_pipeline
from app.jobs.notify_dispatch import run_notify_dispatch

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def scheduler_enabled() -> bool:
    """True only when HUMUMU_ENABLE_SCHEDULER=1 (default off for tests/safety)."""
    return os.environ.get("HUMUMU_ENABLE_SCHEDULER", "").strip() == "1"


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def _digest_cron(settings: Settings) -> CronTrigger:
    """Build daily-summary cron from DIGEST_HOUR / DIGEST_MINUTE / DIGEST_TIMEZONE."""
    hour = int(settings.digest_hour)
    minute = int(settings.digest_minute)
    tz_name = (settings.digest_timezone or "Asia/Shanghai").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        logger.warning("invalid DIGEST_TIMEZONE %r; falling back to Asia/Shanghai", tz_name)
        tz = ZoneInfo("Asia/Shanghai")
        tz_name = "Asia/Shanghai"
    return CronTrigger(hour=hour, minute=minute, timezone=tz)


def start_scheduler(settings: Settings | None = None) -> AsyncIOScheduler | None:
    """
    Start AsyncIOScheduler if enabled via env.

    Jobs:
      - interval fetch every ``fetch_interval_minutes``
      - interval notify dispatch every 2 minutes
      - cron daily summary at DIGEST_HOUR:DIGEST_MINUTE in DIGEST_TIMEZONE
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

    tz_name = (settings.digest_timezone or "Asia/Shanghai").strip()
    try:
        ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        tz_name = "Asia/Shanghai"

    sched = AsyncIOScheduler(timezone=ZoneInfo(tz_name))

    interval_min = max(int(settings.fetch_interval_minutes or 30), 1)
    digest_hour = int(settings.digest_hour)
    digest_minute = int(settings.digest_minute)

    async def _fetch_job() -> None:
        await run_fetch_pipeline(session_factory, settings)

    async def _notify_job() -> None:
        await run_notify_dispatch(session_factory, settings)

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
        _notify_job,
        trigger="interval",
        minutes=2,
        id="notify_dispatch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        _summary_job,
        trigger=_digest_cron(settings),
        id="daily_summary",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    _scheduler = sched
    logger.info(
        "scheduler started: fetch every %d min, notify every 2 min, "
        "daily summary at %02d:%02d %s",
        interval_min,
        digest_hour,
        digest_minute,
        tz_name,
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

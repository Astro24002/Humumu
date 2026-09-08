"""Unit tests for daily-digest cron configuration."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import Settings
from app.jobs.scheduler import _digest_cron


def test_digest_cron_uses_settings_hour_and_timezone():
    s = Settings(
        _env_file=None,
        jwt_secret="x" * 32,
        digest_hour=9,
        digest_minute=15,
        digest_timezone="Asia/Shanghai",
    )
    trigger = _digest_cron(s)
    assert trigger.timezone == ZoneInfo("Asia/Shanghai")
    now = datetime(2026, 9, 8, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    nxt = trigger.get_next_fire_time(None, now)
    assert nxt is not None
    assert nxt.hour == 9 and nxt.minute == 15
    assert nxt.tzinfo == ZoneInfo("Asia/Shanghai")


def test_digest_cron_falls_back_on_bad_timezone():
    s = Settings(
        _env_file=None,
        jwt_secret="x" * 32,
        digest_hour=8,
        digest_minute=0,
        digest_timezone="Totally/Invalid",
    )
    trigger = _digest_cron(s)
    assert trigger.timezone == ZoneInfo("Asia/Shanghai")

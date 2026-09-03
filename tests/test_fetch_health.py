"""Unit tests for journal fetch health recording helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.jobs.fetch_pipeline import record_fetch_failure, record_fetch_success


def _journal(**overrides):
    j = MagicMock()
    j.name = "Nature"
    j.consecutive_failures = 0
    j.is_active = True
    j.last_error = None
    j.last_fetched_at = None
    j.last_success_at = None
    j.etag = None
    j.last_modified = None
    for k, v in overrides.items():
        setattr(j, k, v)
    return j


@pytest.mark.asyncio
async def test_record_fetch_success_resets_failures():
    j = _journal(consecutive_failures=3, last_error="boom")
    session = AsyncMock()
    session.commit = AsyncMock()
    await record_fetch_success(session, j, etag='"abc"', last_modified="Wed, 01 Jan 2026")
    assert j.consecutive_failures == 0
    assert j.last_error is None
    assert j.etag == '"abc"'
    assert j.last_modified == "Wed, 01 Jan 2026"
    assert isinstance(j.last_success_at, datetime)
    assert j.last_success_at.tzinfo is not None
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_record_fetch_failure_increments():
    j = _journal(consecutive_failures=1)
    session = AsyncMock()
    session.commit = AsyncMock()
    await record_fetch_failure(session, j, "timeout")
    assert j.consecutive_failures == 2
    assert j.last_error == "timeout"
    assert j.is_active is True
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_record_fetch_failure_auto_pauses_at_threshold():
    j = _journal(consecutive_failures=9)
    session = AsyncMock()
    session.commit = AsyncMock()
    await record_fetch_failure(session, j, "dns fail", auto_pause_after=10)
    assert j.consecutive_failures == 10
    assert j.is_active is False


@pytest.mark.asyncio
async def test_record_fetch_failure_truncates_error():
    j = _journal()
    session = AsyncMock()
    session.commit = AsyncMock()
    long = "x" * 2000
    await record_fetch_failure(session, j, long)
    assert j.last_error is not None
    assert len(j.last_error) == 1000

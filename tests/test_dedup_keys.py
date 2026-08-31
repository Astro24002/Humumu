"""Unit tests for dedup key format and SET NX semantics (mocked redis)."""

from unittest.mock import AsyncMock

import pytest

from app.services.dedup import DEDUP_TTL_SECONDS, dedup_key, is_duplicate_and_mark


def test_dedup_key_with_doi():
    assert dedup_key("jid-1", "10.1000/xyz", "https://example.org/a") == "dedup:jid-1:10.1000/xyz"


def test_dedup_key_url_fallback():
    assert (
        dedup_key("jid-1", None, "https://example.org/a")
        == "dedup:jid-1:url:https://example.org/a"
    )
    assert (
        dedup_key("jid-1", "", "https://example.org/a")
        == "dedup:jid-1:url:https://example.org/a"
    )
    assert (
        dedup_key("jid-1", "   ", "https://example.org/b")
        == "dedup:jid-1:url:https://example.org/b"
    )


def test_dedup_key_prefers_doi_over_url():
    key = dedup_key("j", "10.1/abc", "https://ignored")
    assert key == "dedup:j:10.1/abc"
    assert ":url:" not in key


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_new():
    r = AsyncMock()
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", "10.1/x", "https://u")
    assert result is True  # True means NEW
    r.set.assert_awaited_once_with(
        "dedup:j1:10.1/x", "1", nx=True, ex=DEDUP_TTL_SECONDS
    )


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_exists():
    r = AsyncMock()
    r.set = AsyncMock(return_value=None)  # redis-py: None when NX fails
    result = await is_duplicate_and_mark(r, "j1", "10.1/x", "https://u")
    assert result is False  # False means duplicate


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_url_key():
    r = AsyncMock()
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", None, "https://cnki.example/a")
    assert result is True
    r.set.assert_awaited_once_with(
        "dedup:j1:url:https://cnki.example/a",
        "1",
        nx=True,
        ex=DEDUP_TTL_SECONDS,
    )


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_no_redis():
    # Missing redis → treat as new
    assert await is_duplicate_and_mark(None, "j1", "10.1/x", "u") is True


@pytest.mark.asyncio
async def test_ttl_is_seven_days():
    assert DEDUP_TTL_SECONDS == 604800

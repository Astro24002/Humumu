"""Unit tests for dedup key format and SET NX semantics (mocked redis)."""

from unittest.mock import AsyncMock

import pytest

from app.services.dedup import (
    DEDUP_TTL_SECONDS,
    dedup_key,
    dedup_keys,
    is_duplicate_and_mark,
)


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


def test_dedup_key_guid_before_url():
    assert (
        dedup_key("j", None, "https://ignored", guid="entry-1")
        == "dedup:j:guid:entry-1"
    )


def test_dedup_key_prefers_doi_over_url_and_guid():
    key = dedup_key("j", "10.1/abc", "https://ignored", guid="g1")
    assert key == "dedup:j:10.1/abc"
    assert ":url:" not in key
    assert ":guid:" not in key


def test_dedup_keys_all_present():
    keys = dedup_keys("j", doi="10.1/x", guid="g", url="https://u")
    assert keys == [
        "dedup:j:10.1/x",
        "dedup:j:guid:g",
        "dedup:j:url:https://u",
    ]


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_new():
    r = AsyncMock()
    r.exists = AsyncMock(return_value=0)
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", "10.1/x", "https://u")
    assert result is True  # True means NEW
    # primary set with NX
    assert r.set.await_args_list[0].args[0] == "dedup:j1:10.1/x"
    assert r.set.await_args_list[0].kwargs["nx"] is True
    assert r.set.await_args_list[0].kwargs["ex"] == DEDUP_TTL_SECONDS


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_exists():
    r = AsyncMock()
    r.exists = AsyncMock(return_value=1)
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", "10.1/x", "https://u")
    assert result is False  # False means duplicate


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_url_key():
    r = AsyncMock()
    r.exists = AsyncMock(return_value=0)
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", None, "https://cnki.example/a")
    assert result is True
    r.set.assert_awaited()
    assert r.set.await_args_list[0].args[0] == "dedup:j1:url:https://cnki.example/a"


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_guid():
    r = AsyncMock()
    r.exists = AsyncMock(return_value=0)
    r.set = AsyncMock(return_value=True)
    result = await is_duplicate_and_mark(r, "j1", None, "", guid="atom-id-9")
    assert result is True
    assert r.set.await_args_list[0].args[0] == "dedup:j1:guid:atom-id-9"


@pytest.mark.asyncio
async def test_is_duplicate_and_mark_no_redis():
    assert await is_duplicate_and_mark(None, "j1", "10.1/x", "u") is True


@pytest.mark.asyncio
async def test_ttl_is_seven_days():
    assert DEDUP_TTL_SECONDS == 604800

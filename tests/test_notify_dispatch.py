"""Unit tests for notification outbox dispatcher (no live SMTP/WeChat)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.notify_dispatch import (
    _BACKOFF_SECONDS,
    _MAX_ATTEMPTS,
    _next_attempt_at,
    dispatch_pending,
)


def test_next_attempt_backoff_steps():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _next_attempt_at(0, now) == now + timedelta(seconds=_BACKOFF_SECONDS[0])
    assert _next_attempt_at(1, now) == now + timedelta(seconds=_BACKOFF_SECONDS[1])
    assert _next_attempt_at(4, now) == now + timedelta(seconds=_BACKOFF_SECONDS[4])
    # clamp beyond table
    assert _next_attempt_at(99, now) == now + timedelta(seconds=_BACKOFF_SECONDS[-1])


def _make_notif(**overrides):
    n = MagicMock()
    n.id = uuid.uuid4()
    n.user_id = uuid.uuid4()
    n.article_id = uuid.uuid4()
    n.channel = "email"
    n.status = "pending"
    n.attempt_count = 0
    n.next_attempt_at = None
    n.error_message = None
    n.sent_at = None
    n.created_at = datetime.now(timezone.utc)
    for k, v in overrides.items():
        setattr(n, k, v)
    return n


def _make_article(**overrides):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.journal_id = uuid.uuid4()
    a.title = "Paper"
    a.authors = ["A"]
    a.abstract = "abs"
    a.url = "https://example.com/p"
    a.doi = "10.1/x"
    for k, v in overrides.items():
        setattr(a, k, v)
    return a


def _make_user(**overrides):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "u@example.com"
    u.wechat_openid = "oid"
    for k, v in overrides.items():
        setattr(u, k, v)
    return u


@pytest.mark.asyncio
async def test_dispatch_success_marks_sent():
    notif = _make_notif()
    article = _make_article(id=notif.article_id)
    user = _make_user(id=notif.user_id)
    journal = MagicMock()
    journal.name = "Nature"

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [notif]
    session.execute = AsyncMock(return_value=result)

    async def _get(model, pk):  # noqa: ANN001
        if model.__name__ == "Article":
            return article
        if model.__name__ == "User":
            return user
        if model.__name__ == "Journal":
            return journal
        return None

    session.get = AsyncMock(side_effect=_get)
    session.commit = AsyncMock()

    email = MagicMock()
    email.send_article.return_value = True
    wechat = MagicMock()
    wechat.send_article = AsyncMock(return_value=True)

    n = await dispatch_pending(session, email_ntfr=email, wechat_ntfr=wechat)
    assert n == 1
    assert notif.status == "sent"
    assert notif.sent_at is not None
    email.send_article.assert_called_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_dispatch_failure_schedules_retry():
    notif = _make_notif(attempt_count=0)
    article = _make_article(id=notif.article_id)
    user = _make_user(id=notif.user_id, email="")
    journal = MagicMock()
    journal.name = "Nature"

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [notif]
    session.execute = AsyncMock(return_value=result)

    async def _get(model, pk):  # noqa: ANN001
        if model.__name__ == "Article":
            return article
        if model.__name__ == "User":
            return user
        if model.__name__ == "Journal":
            return journal
        return None

    session.get = AsyncMock(side_effect=_get)
    session.commit = AsyncMock()

    email = MagicMock()
    email.send_article.return_value = False  # triggers RuntimeError path
    wechat = MagicMock()
    wechat.send_article = AsyncMock(return_value=True)

    n = await dispatch_pending(session, email_ntfr=email, wechat_ntfr=wechat)
    assert n == 1
    assert notif.status == "pending"
    assert notif.attempt_count == 1
    assert notif.next_attempt_at is not None
    assert notif.error_message


@pytest.mark.asyncio
async def test_dispatch_max_attempts_marks_failed():
    notif = _make_notif(attempt_count=_MAX_ATTEMPTS - 1)
    article = _make_article(id=notif.article_id)
    user = _make_user(id=notif.user_id)

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [notif]
    session.execute = AsyncMock(return_value=result)

    async def _get(model, pk):  # noqa: ANN001
        if model.__name__ == "Article":
            return article
        if model.__name__ == "User":
            return user
        if model.__name__ == "Journal":
            return MagicMock(name="J")
        return None

    session.get = AsyncMock(side_effect=_get)
    session.commit = AsyncMock()

    email = MagicMock()
    email.send_article.side_effect = RuntimeError("smtp down")
    wechat = MagicMock()
    wechat.send_article = AsyncMock()

    n = await dispatch_pending(session, email_ntfr=email, wechat_ntfr=wechat)
    assert n == 1
    assert notif.status == "failed"
    assert notif.attempt_count == _MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_dispatch_missing_article_fails():
    notif = _make_notif()
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [notif]
    session.execute = AsyncMock(return_value=result)
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    email = MagicMock()
    wechat = MagicMock()
    wechat.send_article = AsyncMock()

    n = await dispatch_pending(session, email_ntfr=email, wechat_ntfr=wechat)
    assert n == 1
    assert notif.status == "failed"
    assert "article missing" in (notif.error_message or "")

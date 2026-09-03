"""Notification outbox dispatcher: send pending rows with retry/backoff."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.models.article import Article
from app.models.journal import Journal
from app.models.notification import Notification
from app.models.user import User
from app.services.notifier_email import EmailNotifier
from app.services.notifier_wechat import WeChatNotifier

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_BACKOFF_SECONDS = (60, 300, 1800, 7200, 14400)  # 1m, 5m, 30m, 2h, 4h
_BATCH_LIMIT = 100


def _next_attempt_at(attempt_count: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    idx = min(max(attempt_count, 0), len(_BACKOFF_SECONDS) - 1)
    return now + timedelta(seconds=_BACKOFF_SECONDS[idx])


async def _send_notification(
    *,
    notif: Notification,
    article: Article,
    journal_name: str,
    user: User | None,
    email_ntfr: EmailNotifier,
    wechat_ntfr: WeChatNotifier,
) -> None:
    doi = article.doi or ""
    if notif.channel == "email":
        to_email = (user.email if user else "") or ""
        sent = email_ntfr.send_article(
            to_email=to_email,
            journal_name=journal_name,
            title=article.title or "",
            authors=list(article.authors or []),
            abstract=article.abstract or "",
            url=article.url or "",
            doi=doi,
        )
        if not sent:
            raise RuntimeError("email not configured or user has no email")
    elif notif.channel == "wechat":
        openid = (user.wechat_openid if user else None) or ""
        sent = await wechat_ntfr.send_article(
            openid=openid,
            journal_name=journal_name,
            title=article.title or "",
            authors=list(article.authors or []),
            abstract=article.abstract or "",
            doi=doi,
        )
        if not sent:
            raise RuntimeError("wechat not configured or user has no openid")
    else:
        raise RuntimeError(f"unknown channel: {notif.channel}")


async def dispatch_pending(
    session: AsyncSession,
    *,
    email_ntfr: EmailNotifier,
    wechat_ntfr: WeChatNotifier,
    limit: int = _BATCH_LIMIT,
) -> int:
    """Process up to ``limit`` pending notifications. Returns processed count."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Notification)
        .where(
            Notification.status == "pending",
            or_(
                Notification.next_attempt_at.is_(None),
                Notification.next_attempt_at <= now,
            ),
        )
        .order_by(Notification.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    try:
        result = await session.execute(stmt)
        pending = list(result.scalars().all())
    except Exception:
        # SQLite/tests or DBs without FOR UPDATE SKIP LOCKED — fallback
        stmt = (
            select(Notification)
            .where(
                Notification.status == "pending",
                or_(
                    Notification.next_attempt_at.is_(None),
                    Notification.next_attempt_at <= now,
                ),
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        pending = list(result.scalars().all())

    processed = 0
    for notif in pending:
        processed += 1
        article = await session.get(Article, notif.article_id)
        user = await session.get(User, notif.user_id)
        journal_name = ""
        if article is not None:
            journal = await session.get(Journal, article.journal_id)
            journal_name = (journal.name if journal else "") or ""

        if article is None:
            notif.status = "failed"
            notif.error_message = "article missing"
            continue

        try:
            await _send_notification(
                notif=notif,
                article=article,
                journal_name=journal_name,
                user=user,
                email_ntfr=email_ntfr,
                wechat_ntfr=wechat_ntfr,
            )
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            notif.error_message = None
        except Exception as exc:  # noqa: BLE001 — isolate per channel/row
            logger.warning(
                "notify_dispatch: send failed [%s/%s]: %s",
                notif.channel,
                notif.id,
                exc,
            )
            notif.attempt_count = int(notif.attempt_count or 0) + 1
            notif.error_message = str(exc)[:500]
            if notif.attempt_count >= _MAX_ATTEMPTS:
                notif.status = "failed"
            else:
                notif.status = "pending"
                notif.next_attempt_at = _next_attempt_at(notif.attempt_count)

    await session.commit()
    return processed


async def run_notify_dispatch(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    email_ntfr = EmailNotifier(settings)
    wechat_ntfr = WeChatNotifier(settings)
    async with session_factory() as session:
        n = await dispatch_pending(
            session, email_ntfr=email_ntfr, wechat_ntfr=wechat_ntfr
        )
        if n:
            logger.info("notify_dispatch: processed %d notifications", n)


# Exported for unit tests
__all__ = [
    "dispatch_pending",
    "run_notify_dispatch",
    "_next_attempt_at",
    "_MAX_ATTEMPTS",
    "_BACKOFF_SECONDS",
]

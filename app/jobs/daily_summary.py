"""Daily summary job for users with push_frequency=daily."""

from __future__ import annotations

import logging
from datetime import date as date_cls
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.models.article import Article
from app.models.journal import Journal
from app.models.notification import Notification
from app.models.subscription import JournalSubscription
from app.models.user import User
from app.services import notify_content as nc
from app.services.notifier_email import EmailNotifier
from app.services.notifier_wechat import WeChatNotifier

logger = logging.getLogger(__name__)


async def _articles_for_user_since(
    session: AsyncSession,
    user_id: UUID,
    since: datetime,
) -> list[dict[str, Any]]:
    stmt = (
        select(Article, Journal.name)
        .join(JournalSubscription, Article.journal_id == JournalSubscription.journal_id)
        .outerjoin(Journal, Article.journal_id == Journal.id)
        .where(
            JournalSubscription.user_id == user_id,
            Article.fetched_at >= since,
        )
        .order_by(Article.fetched_at.asc())
    )
    rows = (await session.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for article, journal_name in rows:
        out.append(
            {
                "id": article.id,
                "title": article.title or "",
                "url": article.url or "",
                "doi": article.doi or "",
                "authors": list(article.authors or []),
                "abstract": article.abstract or "",
                "journal_name": journal_name or "",
            }
        )
    return out


async def run_daily_summary(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    """Send daily digests to users with push_frequency=daily."""
    settings = settings or get_settings()
    email_ntfr = EmailNotifier(settings)
    wechat_ntfr = WeChatNotifier(settings)

    logger.info("daily summary: starting")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today_label = date_cls.today().isoformat()

    async with session_factory() as session:
        users = list(
            (
                await session.execute(
                    select(User).where(User.push_frequency == "daily")
                )
            )
            .scalars()
            .all()
        )

        if not users:
            logger.info("daily summary: no daily users")
            return

        for user in users:
            try:
                articles = await _articles_for_user_since(session, user.id, since)
                if not articles:
                    continue

                openid = (user.wechat_openid or "").strip()
                wechat_ok = bool(openid) and bool(
                    getattr(user, "wechat_template_subscribed", False)
                )
                email_ok = nc.is_real_email(user.email or "")
                # Prefer WeChat when template-subscribed; else email.
                channel = "wechat" if wechat_ok else "email"
                sent = False
                send_err: str | None = None
                try:
                    if channel == "wechat":
                        sent = await wechat_ntfr.send_summary(
                            openid=openid,
                            articles=articles,
                            date_label=today_label,
                        )
                        if not sent and email_ok:
                            # fall back to email if wechat skipped
                            sent = email_ntfr.send_summary(
                                to_email=user.email or "",
                                articles=articles,
                                date_label=today_label,
                            )
                            if sent:
                                channel = "email"
                            else:
                                send_err = "wechat/email not configured"
                        elif not sent:
                            send_err = "wechat not configured or not subscribed"
                    else:
                        sent = email_ntfr.send_summary(
                            to_email=user.email or "",
                            articles=articles,
                            date_label=today_label,
                        )
                        if not sent:
                            send_err = "email not configured or user has no real email"
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "daily summary: send error for user %s: %s", user.id, exc
                    )
                    send_err = str(exc)[:500]

                status = "sent" if sent else "failed"
                now = datetime.now(timezone.utc) if sent else None
                for a in articles:
                    n = Notification(
                        user_id=user.id,
                        article_id=a["id"],
                        channel=channel,
                        status=status,
                        error_message=send_err,
                        sent_at=now,
                    )
                    session.add(n)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "daily summary: failed for user %s: %s", user.id, exc
                )
                await session.rollback()

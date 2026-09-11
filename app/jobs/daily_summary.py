"""Daily summary job for users with push_frequency=daily."""

from __future__ import annotations

import logging
from datetime import date as date_cls
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.models.article import Article
from app.models.journal import Journal
from app.models.notification import Notification
from app.models.subscription import AuthorTracking, JournalSubscription, KeywordSubscription
from app.models.user import User
from app.services import notify_content as nc
from app.services.matcher import effective_push_frequency, match_authors, match_keywords
from app.services.notifier_email import EmailNotifier
from app.services.notifier_wechat import WeChatNotifier

logger = logging.getLogger(__name__)


def select_digest_articles(
    *,
    user_id: str,
    user_push_freq: str,
    articles: Sequence[dict[str, Any]],
    journal_subs: Sequence[tuple[str, str]],
    tracked_authors: Sequence[str],
    keywords: Sequence[str],
) -> list[dict[str, Any]]:
    """
    Pick digest items: daily journal subs ∪ (author/keyword if user default is daily).

    Journal hits only when effective frequency is daily (realtime override skipped).
    Author/keyword hits go to digest only for daily-default users; realtime-default
    users already get those via notify_dispatch.
    """
    daily_journals: set[str] = set()
    for jid, freq in journal_subs:
        if effective_push_frequency(freq, user_push_freq) == "daily":
            daily_journals.add(str(jid))

    author_kw_ok = effective_push_frequency("default", user_push_freq) == "daily"
    tracked = [(user_id, name) for name in tracked_authors] if author_kw_ok else []
    kws = [(user_id, kw) for kw in keywords] if author_kw_ok else []

    out: list[dict[str, Any]] = []
    for a in articles:
        reasons: list[str] = []
        jid = str(a.get("journal_id") or "")
        if jid and jid in daily_journals:
            reasons.append("journal")
        if tracked and match_authors(
            article_id="x",
            article_authors=list(a.get("authors") or []),
            tracked=tracked,
        ):
            reasons.append("author")
        if kws and match_keywords(
            article_id="x",
            title=a.get("title") or "",
            abstract=a.get("abstract") or "",
            keywords=kws,
        ):
            reasons.append("keyword")
        if not reasons:
            continue
        row = dict(a)
        row["match_reasons"] = reasons
        out.append(row)
    return out


async def _recent_articles(
    session: AsyncSession, since: datetime
) -> list[dict[str, Any]]:
    stmt = (
        select(Article, Journal.name)
        .outerjoin(Journal, Article.journal_id == Journal.id)
        .where(Article.fetched_at >= since)
        .order_by(Article.fetched_at.asc())
    )
    rows = (await session.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for article, journal_name in rows:
        out.append(
            {
                "id": article.id,
                "journal_id": str(article.journal_id) if article.journal_id else "",
                "title": article.title or "",
                "url": article.url or "",
                "doi": article.doi or "",
                "authors": list(article.authors or []),
                "abstract": article.abstract or "",
                "journal_name": journal_name or "",
            }
        )
    return out


async def _load_digest_inputs(
    session: AsyncSession,
    user_ids: Sequence[UUID],
    since: datetime,
) -> tuple[
    list[dict[str, Any]],
    dict[str, list[tuple[str, str]]],
    dict[str, list[str]],
    dict[str, list[str]],
]:
    articles = await _recent_articles(session, since)
    if not user_ids:
        return articles, {}, {}, {}

    subs_by_user: dict[str, list[tuple[str, str]]] = {str(uid): [] for uid in user_ids}
    sub_rows = (
        await session.execute(
            select(
                JournalSubscription.user_id,
                JournalSubscription.journal_id,
                JournalSubscription.push_frequency,
            ).where(JournalSubscription.user_id.in_(user_ids))
        )
    ).all()
    for uid, jid, freq in sub_rows:
        subs_by_user.setdefault(str(uid), []).append((str(jid), freq or "default"))

    authors_by_user: dict[str, list[str]] = {str(uid): [] for uid in user_ids}
    author_rows = (
        await session.execute(
            select(AuthorTracking.user_id, AuthorTracking.author_name).where(
                AuthorTracking.user_id.in_(user_ids)
            )
        )
    ).all()
    for uid, name in author_rows:
        authors_by_user.setdefault(str(uid), []).append(name or "")

    kws_by_user: dict[str, list[str]] = {str(uid): [] for uid in user_ids}
    kw_rows = (
        await session.execute(
            select(KeywordSubscription.user_id, KeywordSubscription.keyword).where(
                KeywordSubscription.user_id.in_(user_ids)
            )
        )
    ).all()
    for uid, kw in kw_rows:
        kws_by_user.setdefault(str(uid), []).append(kw or "")

    return articles, subs_by_user, authors_by_user, kws_by_user


async def run_daily_summary(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    """Send daily digests to users with daily default or a daily journal override."""
    settings = settings or get_settings()
    email_ntfr = EmailNotifier(settings)
    wechat_ntfr = WeChatNotifier(settings)

    logger.info("daily summary: starting")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    today_label = date_cls.today().isoformat()

    async with session_factory() as session:
        daily_journal_override = exists(
            select(1).where(
                JournalSubscription.user_id == User.id,
                JournalSubscription.push_frequency == "daily",
            )
        )
        users = list(
            (
                await session.execute(
                    select(User).where(
                        or_(
                            User.push_frequency == "daily",
                            daily_journal_override,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

        if not users:
            logger.info("daily summary: no digest users")
            return

        articles, subs_by_user, authors_by_user, kws_by_user = await _load_digest_inputs(
            session, [u.id for u in users], since
        )

        for user in users:
            try:
                uid = str(user.id)
                picked = select_digest_articles(
                    user_id=uid,
                    user_push_freq=user.push_frequency or "daily",
                    articles=articles,
                    journal_subs=subs_by_user.get(uid) or [],
                    tracked_authors=authors_by_user.get(uid) or [],
                    keywords=kws_by_user.get(uid) or [],
                )
                if not picked:
                    continue

                openid = (user.wechat_openid or "").strip()
                wechat_ok = bool(openid) and bool(
                    getattr(user, "wechat_template_subscribed", False)
                )
                email_ok = nc.is_real_email(user.email or "")
                if not wechat_ok and not email_ok:
                    continue

                # Prefer WeChat when template-subscribed; else email.
                channel = "wechat" if wechat_ok else "email"
                sent = False
                send_err: str | None = None
                try:
                    if channel == "wechat":
                        sent = await wechat_ntfr.send_summary(
                            openid=openid,
                            articles=picked,
                            date_label=today_label,
                        )
                        if not sent and email_ok:
                            sent = email_ntfr.send_summary(
                                to_email=user.email or "",
                                articles=picked,
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
                            articles=picked,
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
                for a in picked:
                    reasons = a.get("match_reasons") or []
                    n = Notification(
                        user_id=user.id,
                        article_id=a["id"],
                        channel=channel,
                        status=status,
                        error_message=send_err,
                        sent_at=now,
                        match_reasons=",".join(reasons) if reasons else "",
                    )
                    session.add(n)
                await session.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "daily summary: failed for user %s: %s", user.id, exc
                )
                await session.rollback()

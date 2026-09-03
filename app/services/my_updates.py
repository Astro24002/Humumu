"""My Updates feed: articles matched to the user's subscriptions + reading status."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.article import Article
from app.models.journal import Journal
from app.models.notification import Notification
from app.models.subscription import JournalSubscription
from app.models.user_article_status import UserArticleStatus


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _clamp_limit(limit: int) -> int:
    if limit > 50:
        return 50
    if limit < 1:
        return 1
    return limit


async def list_my_updates(
    session: AsyncSession,
    user_id: str | UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    filter_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return article cards for the authenticated user.

    Sources:
      - articles from journals the user subscribes to
      - articles that produced a notification for the user (author/keyword hits)

    Visibility: subscribed journals always OK; else journal must be public or owned.
    """
    uid = _parse_uuid(user_id)
    if uid is None:
        return []
    limit = _clamp_limit(limit)
    if offset < 0:
        offset = 0

    sub_articles = (
        select(Article.id.label("id"))
        .join(JournalSubscription, JournalSubscription.journal_id == Article.journal_id)
        .where(JournalSubscription.user_id == uid)
    )
    notif_articles = select(Notification.article_id.label("id")).where(
        Notification.user_id == uid
    )
    article_ids_q = sub_articles.union(notif_articles).subquery()

    status = aliased(UserArticleStatus)
    visibility = or_(
        Journal.directory_status == "public",
        Journal.created_by == uid,
        Journal.id.in_(
            select(JournalSubscription.journal_id).where(JournalSubscription.user_id == uid)
        ),
    )

    stmt = (
        select(Article, Journal, status, Notification.match_reasons)
        .join(article_ids_q, article_ids_q.c.id == Article.id)
        .join(Journal, Journal.id == Article.journal_id)
        .outerjoin(
            status,
            and_(status.user_id == uid, status.article_id == Article.id),
        )
        .outerjoin(
            Notification,
            and_(Notification.user_id == uid, Notification.article_id == Article.id),
        )
        .where(visibility)
        .order_by(Article.fetched_at.desc())
        .limit(limit * 3)  # headroom for notification dup rows before dedupe
        .offset(offset)
    )

    filt = (filter_name or "").strip().lower()
    if filt == "starred":
        stmt = stmt.where(status.is_starred.is_(True))
    elif filt == "later":
        stmt = stmt.where(status.is_later.is_(True))
    elif filt == "unread":
        stmt = stmt.where(or_(status.user_id.is_(None), status.is_read.is_(False)))

    result = await session.execute(stmt)
    rows = result.all()

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for article, journal, st, match_reasons in rows:
        aid = str(article.id)
        if aid in seen:
            continue
        seen.add(aid)
        reasons = [p for p in str(match_reasons or "").split(",") if p]
        status_out = {
            "is_read": bool(st.is_read) if st is not None else False,
            "is_starred": bool(st.is_starred) if st is not None else False,
            "is_later": bool(st.is_later) if st is not None else False,
            "original_clicked_at": st.original_clicked_at if st is not None else None,
        }
        out.append(
            {
                "article_id": aid,
                "title": article.title or "",
                "authors": list(article.authors or []),
                "abstract": article.abstract or "",
                "doi": article.doi,
                "url": article.url or "",
                "original_url": article.url or "",
                "publish_date": article.publish_date.isoformat()
                if article.publish_date
                else None,
                "fetched_at": article.fetched_at,
                "journal_id": str(journal.id),
                "journal_name": journal.name or "",
                "content_type": getattr(journal, "content_type", None) or "journal",
                "reasons": reasons,
                "status": status_out,
            }
        )
        if len(out) >= limit:
            break
    return out

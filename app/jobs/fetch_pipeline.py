"""Fetch → dedup → insert → match → enqueue pipeline for active journals.

Only enqueue notifications (status=pending) — sending is decoupled to notify_dispatch.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.models.article import Article
from app.models.journal import Journal
from app.models.notification import Notification
from app.models.subscription import AuthorTracking, JournalSubscription, KeywordSubscription
from app.models.user import User
from app.redis_client import get_redis
from app.services.dedup import is_duplicate_and_mark
from app.services.fetcher import RawArticle, fetch_articles
from app.services.matcher import match_article

logger = logging.getLogger(__name__)

_AUTO_PAUSE_FAILURES = 10


def _parse_publish_date(raw: str) -> date | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


async def _load_match_context(session: AsyncSession) -> dict[str, Any]:
    """Load authors, keywords, and user openids once per cycle."""
    authors_rows = (
        await session.execute(select(AuthorTracking.user_id, AuthorTracking.author_name))
    ).all()
    tracked_authors = [(str(uid), name) for uid, name in authors_rows]

    kw_rows = (
        await session.execute(
            select(KeywordSubscription.user_id, KeywordSubscription.keyword)
        )
    ).all()
    keywords = [(str(uid), kw) for uid, kw in kw_rows]

    user_rows = (await session.execute(select(User.id, User.wechat_openid, User.email))).all()
    user_openid: dict[str, str | None] = {
        str(uid): openid for uid, openid, _email in user_rows
    }
    user_email: dict[str, str] = {
        str(uid): (email or "") for uid, _openid, email in user_rows
    }
    return {
        "tracked_authors": tracked_authors,
        "keywords": keywords,
        "user_openid": user_openid,
        "user_email": user_email,
    }


async def _journal_subscriber_ids(session: AsyncSession, journal_id: UUID) -> list[str]:
    rows = (
        await session.execute(
            select(JournalSubscription.user_id).where(
                JournalSubscription.journal_id == journal_id
            )
        )
    ).all()
    return [str(r[0]) for r in rows]


async def record_fetch_success(
    session: AsyncSession,
    journal: Journal,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    journal.last_fetched_at = now
    journal.last_success_at = now
    journal.consecutive_failures = 0
    journal.last_error = None
    if etag is not None:
        journal.etag = etag or None
    if last_modified is not None:
        journal.last_modified = last_modified or None
    await session.commit()


async def record_fetch_failure(
    session: AsyncSession,
    journal: Journal,
    error: str,
    *,
    auto_pause_after: int = _AUTO_PAUSE_FAILURES,
) -> None:
    now = datetime.now(timezone.utc)
    journal.last_fetched_at = now
    journal.consecutive_failures = int(journal.consecutive_failures or 0) + 1
    journal.last_error = (error or "")[:1000] or None
    if journal.consecutive_failures >= auto_pause_after:
        journal.is_active = False
        logger.warning(
            "pipeline: auto-paused journal %s after %d failures",
            journal.name,
            journal.consecutive_failures,
        )
    await session.commit()


async def process_raw_article(
    session: AsyncSession,
    *,
    journal: Journal,
    raw: RawArticle,
    match_ctx: dict[str, Any],
) -> None:
    """Dedup, insert, match, and enqueue pending notifications (no inline send)."""
    r = get_redis()
    journal_id = str(journal.id)
    doi = _empty_to_none(raw.get("doi"))
    guid = _empty_to_none(raw.get("guid"))
    url = raw.get("url") or ""

    is_new = await is_duplicate_and_mark(r, journal_id, doi, url, guid=guid)
    if not is_new:
        return

    article = Article(
        doi=doi,
        guid=guid,
        title=raw.get("title") or "",
        authors=list(raw.get("authors") or []),
        abstract=raw.get("abstract") or "",
        journal_id=journal.id,
        publish_date=_parse_publish_date(raw.get("publish_date") or ""),
        url=url,
    )
    session.add(article)
    try:
        await session.flush()
    except IntegrityError:
        logger.info(
            "pipeline: DB unique hit (dup) [%s/%s]",
            journal.name,
            doi or guid or url,
        )
        await session.rollback()
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pipeline: save article failed [%s/%s]: %s",
            journal.name,
            doi or guid or url,
            exc,
        )
        await session.rollback()
        return

    subscribers = await _journal_subscriber_ids(session, journal.id)
    matches = match_article(
        article_id=str(article.id),
        journal_subscriber_ids=subscribers,
        article_authors=list(article.authors or []),
        title=article.title or "",
        abstract=article.abstract or "",
        tracked_authors=match_ctx["tracked_authors"],
        keywords=match_ctx["keywords"],
        user_openid=match_ctx["user_openid"],
    )

    for m in matches:
        reasons = getattr(m, "reasons", ()) or ()
        n = Notification(
            user_id=UUID(m.user_id),
            article_id=article.id,
            channel=m.channel,
            status="pending",
            match_reasons=",".join(reasons) if reasons else "",
        )
        session.add(n)

    await session.commit()


async def run_fetch_pipeline(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings | None = None,
) -> None:
    """Run one full fetch cycle over all active journals."""
    _ = settings or get_settings()

    logger.info("scheduler: starting fetch cycle")
    async with session_factory() as session:
        result = await session.execute(
            select(Journal).where(Journal.is_active.is_(True)).order_by(Journal.name)
        )
        journals = list(result.scalars().all())
        if not journals:
            logger.info("scheduler: no active journals to fetch")
            return
        match_ctx = await _load_match_context(session)

    for journal in journals:
        try:
            raws = await fetch_articles(journal.source_url, journal.source_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler: fetch failed [%s]: %s", journal.name, exc)
            try:
                async with session_factory() as session:
                    j = await session.get(Journal, journal.id)
                    if j is not None:
                        await record_fetch_failure(session, j, str(exc))
            except Exception as rec_exc:  # noqa: BLE001
                logger.warning("scheduler: failed to record fetch failure: %s", rec_exc)
            continue

        try:
            async with session_factory() as session:
                j = await session.get(Journal, journal.id)
                if j is not None:
                    await record_fetch_success(session, j)
        except Exception as rec_exc:  # noqa: BLE001
            logger.warning("scheduler: failed to record fetch success: %s", rec_exc)

        logger.info(
            "scheduler: fetched %d articles from %s",
            len(raws),
            journal.name,
        )
        for raw in raws:
            try:
                async with session_factory() as session:
                    j = await session.get(Journal, journal.id)
                    if j is None:
                        continue
                    await process_raw_article(
                        session,
                        journal=j,
                        raw=raw,
                        match_ctx=match_ctx,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "scheduler: process article error [%s/%s]: %s",
                    journal.name,
                    raw.get("doi") or raw.get("guid") or raw.get("url"),
                    exc,
                )

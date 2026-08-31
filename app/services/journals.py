"""Journal query helpers (public list/get with article stats)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.journal import Journal, JournalRequest
from app.schemas.journal import JournalOut, JournalRequestOut


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def slugify(name: str) -> str:
    """Convert a name into a URL-friendly slug (matches Go intent)."""
    s = name.lower()
    # Keep alnum, CJK unified ideographs, spaces, hyphens
    s = re.sub(r"[^a-z0-9一-鿿\s-]", "", s)
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    if not s:
        s = "journal"
    return s


def _journal_out(
    journal: Journal,
    *,
    article_count: int = 0,
    last_article_date: datetime | None = None,
) -> JournalOut:
    return JournalOut.model_validate(
        {
            "id": journal.id,
            "name": journal.name,
            "slug": journal.slug,
            "source_type": journal.source_type,
            "source_url": journal.source_url,
            "description": journal.description or "",
            "fetch_interval": journal.fetch_interval,
            "is_active": journal.is_active,
            "created_by": journal.created_by,
            "created_at": journal.created_at,
            "article_count": int(article_count or 0),
            "last_article_date": last_article_date,
        }
    )


def _request_out(req: JournalRequest) -> JournalRequestOut:
    return JournalRequestOut.model_validate(req)


def _stats_subquery() -> Any:
    return (
        select(
            Article.journal_id.label("journal_id"),
            func.count().label("article_count"),
            func.max(Article.publish_date).label("last_article_date"),
        )
        .group_by(Article.journal_id)
        .subquery()
    )


async def list_journals(session: AsyncSession) -> list[JournalOut]:
    """List all journals ordered by name, with article_count and last_article_date."""
    stats = _stats_subquery()
    stmt = (
        select(
            Journal,
            func.coalesce(stats.c.article_count, 0).label("article_count"),
            stats.c.last_article_date,
        )
        .outerjoin(stats, Journal.id == stats.c.journal_id)
        .order_by(Journal.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        _journal_out(row[0], article_count=row[1], last_article_date=row[2])
        for row in rows
    ]


async def get_journal(session: AsyncSession, journal_id: str | UUID) -> JournalOut | None:
    """Get one journal by id with article stats, or None if missing/invalid id."""
    uid = _parse_uuid(journal_id)
    if uid is None:
        return None

    stats = _stats_subquery()
    stmt = (
        select(
            Journal,
            func.coalesce(stats.c.article_count, 0).label("article_count"),
            stats.c.last_article_date,
        )
        .outerjoin(stats, Journal.id == stats.c.journal_id)
        .where(Journal.id == uid)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return _journal_out(row[0], article_count=row[1], last_article_date=row[2])


async def find_by_url(session: AsyncSession, source_url: str) -> JournalOut | None:
    """Find journal by exact source_url (with article stats), or None."""
    stats = _stats_subquery()
    stmt = (
        select(
            Journal,
            func.coalesce(stats.c.article_count, 0).label("article_count"),
            stats.c.last_article_date,
        )
        .outerjoin(stats, Journal.id == stats.c.journal_id)
        .where(Journal.source_url == source_url)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return _journal_out(row[0], article_count=row[1], last_article_date=row[2])


async def create_journal(
    session: AsyncSession,
    *,
    name: str,
    source_url: str,
    created_by: str | UUID | None = None,
    source_type: str = "rss",
    description: str = "",
    fetch_interval: timedelta | None = None,
    slug: str | None = None,
) -> JournalOut:
    """Create a user/self-service journal and return JournalOut (no stats yet)."""
    uid = _parse_uuid(created_by) if created_by is not None else None
    journal = Journal(
        name=name,
        slug=slug or slugify(name),
        source_type=source_type or "rss",
        source_url=source_url,
        description=description or "",
        fetch_interval=fetch_interval if fetch_interval is not None else timedelta(minutes=30),
        is_active=True,
        created_by=uid,
    )
    session.add(journal)
    await session.flush()
    await session.refresh(journal)
    return _journal_out(journal, article_count=0, last_article_date=None)


async def create_journal_request(
    session: AsyncSession,
    *,
    user_id: str | UUID,
    journal_name: str,
    source_url: str,
) -> JournalRequestOut:
    uid = _parse_uuid(user_id)
    if uid is None:
        raise ValueError("invalid user id")

    req = JournalRequest(
        user_id=uid,
        journal_name=journal_name,
        source_url=source_url,
        status="pending",
    )
    session.add(req)
    await session.flush()
    await session.refresh(req)
    return _request_out(req)


async def list_journal_requests_by_user(
    session: AsyncSession,
    user_id: str | UUID,
) -> list[JournalRequestOut]:
    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(JournalRequest)
        .where(JournalRequest.user_id == uid)
        .order_by(JournalRequest.created_at.desc())
    )
    result = await session.execute(stmt)
    return [_request_out(row) for row in result.scalars().all()]

"""Journal query helpers (public list/get with article stats)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.journal import Journal
from app.schemas.journal import JournalOut


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


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

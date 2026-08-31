"""Article query helpers (public list/get and subscription feed)."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.models.journal import Journal
from app.models.subscription import JournalSubscription
from app.schemas.article import ArticleOut


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _clamp_limit(limit: int) -> int:
    if limit > 100:
        return 100
    return limit


def _article_out(
    article: Article,
    *,
    journal_name: str | None = None,
    journal_source_type: str | None = None,
) -> ArticleOut:
    return ArticleOut.model_validate(
        {
            "id": article.id,
            "doi": article.doi if article.doi is not None else "",
            "title": article.title,
            "authors": list(article.authors or []),
            "abstract": article.abstract or "",
            "journal_id": article.journal_id,
            "journal_name": journal_name or "",
            "journal_source_type": journal_source_type or "",
            "publish_date": article.publish_date,
            "url": article.url or "",
            "fetched_at": article.fetched_at,
        }
    )


def _base_article_select() -> Any:
    return (
        select(
            Article,
            Journal.name.label("journal_name"),
            Journal.source_type.label("journal_source_type"),
        )
        .outerjoin(Journal, Article.journal_id == Journal.id)
        .order_by(Article.publish_date.desc().nulls_last(), Article.fetched_at.desc())
    )


def _rows_to_articles(rows: list[Any]) -> list[ArticleOut]:
    return [
        _article_out(row[0], journal_name=row[1], journal_source_type=row[2])
        for row in rows
    ]


async def list_articles(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    journal_id: str | UUID | None = None,
) -> list[ArticleOut]:
    """Public article list: all articles or filtered by journal_id."""
    limit = _clamp_limit(limit)
    if offset < 0:
        offset = 0

    stmt = _base_article_select()

    if journal_id is not None and str(journal_id) != "":
        uid = _parse_uuid(journal_id)
        if uid is None:
            return []
        stmt = stmt.where(Article.journal_id == uid)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return _rows_to_articles(list(result.all()))


async def get_article(session: AsyncSession, article_id: str | UUID) -> ArticleOut | None:
    """Get one article by id with joined journal fields, or None."""
    uid = _parse_uuid(article_id)
    if uid is None:
        return None

    stmt = _base_article_select().where(Article.id == uid)
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return _article_out(row[0], journal_name=row[1], journal_source_type=row[2])


async def list_feed_for_user(
    session: AsyncSession,
    user_id: str | UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[ArticleOut]:
    """Articles from journals the user is subscribed to."""
    limit = _clamp_limit(limit)
    if offset < 0:
        offset = 0

    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(
            Article,
            Journal.name.label("journal_name"),
            Journal.source_type.label("journal_source_type"),
        )
        .join(JournalSubscription, Article.journal_id == JournalSubscription.journal_id)
        .outerjoin(Journal, Article.journal_id == Journal.id)
        .where(JournalSubscription.user_id == uid)
        .order_by(Article.publish_date.desc().nulls_last(), Article.fetched_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return _rows_to_articles(list(result.all()))


async def count_articles(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Article))
    return int(result.scalar_one() or 0)

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
    content_type: str | None = None,
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
            "content_type": content_type or "journal",
            "publish_date": article.publish_date,
            "url": article.url or "",
            "fetched_at": article.fetched_at,
        }
    )


def _base_article_select(*, public_only: bool = False) -> Any:
    stmt = (
        select(
            Article,
            Journal.name.label("journal_name"),
            Journal.source_type.label("journal_source_type"),
            Journal.content_type.label("content_type"),
        )
        .join(Journal, Article.journal_id == Journal.id)
        .order_by(Article.publish_date.desc().nulls_last(), Article.fetched_at.desc())
    )
    if public_only:
        stmt = stmt.where(Journal.directory_status == "public")
    return stmt


def _rows_to_articles(rows: list[Any]) -> list[ArticleOut]:
    return [
        _article_out(
            row[0],
            journal_name=row[1],
            journal_source_type=row[2],
            content_type=row[3],
        )
        for row in rows
    ]


def _article_filter_stmt(
    *,
    public_only: bool = True,
    journal_id: str | UUID | None = None,
    content_type: str | None = None,
    source_type: str | None = None,
    viewer_user_id: str | UUID | None = None,
    allow_subscribed: bool = False,
) -> Any | None:
    """Build filtered article+journal select without limit/offset.

    Returns None when journal_id is present but invalid (caller should treat as empty).

    public_only visibility:
    - Catalog (no journal_id): only directory_status=public.
    - With journal_id + viewer: public OR created_by == viewer
      OR (allow_subscribed and viewer has JournalSubscription).
    """
    # Apply public filter ourselves so we can add owner/subscriber exceptions.
    stmt = _base_article_select(public_only=False)
    if journal_id is not None and str(journal_id) != "":
        uid = _parse_uuid(journal_id)
        if uid is None:
            return None
        stmt = stmt.where(Article.journal_id == uid)
    if content_type and str(content_type).strip():
        stmt = stmt.where(Journal.content_type == str(content_type).strip())
    if source_type and str(source_type).strip():
        stmt = stmt.where(Journal.source_type == str(source_type).strip().lower())
    if public_only:
        viewer = _parse_uuid(viewer_user_id) if viewer_user_id is not None else None
        if viewer is not None and journal_id is not None and str(journal_id) != "":
            from app.models.subscription import JournalSubscription

            owner_or_public = (Journal.directory_status == "public") | (
                Journal.created_by == viewer
            )
            if allow_subscribed:
                sub_exists = (
                    select(JournalSubscription.journal_id)
                    .where(
                        JournalSubscription.user_id == viewer,
                        JournalSubscription.journal_id == Journal.id,
                    )
                    .exists()
                )
                stmt = stmt.where(owner_or_public | sub_exists)
            else:
                stmt = stmt.where(owner_or_public)
        else:
            stmt = stmt.where(Journal.directory_status == "public")
    return stmt


async def list_articles(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    journal_id: str | UUID | None = None,
    content_type: str | None = None,
    source_type: str | None = None,
    public_only: bool = True,
    viewer_user_id: str | UUID | None = None,
) -> list[ArticleOut]:
    """Public article list: articles from public journals, optional journal_id filter.

    When journal_id is set, viewer may see non-public journals they own or subscribe to.
    """
    limit = _clamp_limit(limit)
    if offset < 0:
        offset = 0

    stmt = _article_filter_stmt(
        public_only=public_only,
        journal_id=journal_id,
        content_type=content_type,
        source_type=source_type,
        viewer_user_id=viewer_user_id,
        allow_subscribed=True,
    )
    if stmt is None:
        return []

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return _rows_to_articles(list(result.all()))


async def count_list_articles(
    session: AsyncSession,
    *,
    journal_id: str | UUID | None = None,
    content_type: str | None = None,
    source_type: str | None = None,
    public_only: bool = True,
    viewer_user_id: str | UUID | None = None,
) -> int:
    """Count articles matching the same filters as list_articles."""
    base = _article_filter_stmt(
        public_only=public_only,
        journal_id=journal_id,
        content_type=content_type,
        source_type=source_type,
        viewer_user_id=viewer_user_id,
        allow_subscribed=True,
    )
    if base is None:
        return 0
    # Re-select count over the filtered join (drop ORDER BY for efficiency).
    stmt = select(func.count()).select_from(base.order_by(None).subquery())
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def get_article(
    session: AsyncSession,
    article_id: str | UUID,
    *,
    public_only: bool = True,
    viewer_user_id: str | UUID | None = None,
) -> ArticleOut | None:
    """Get one article by id with joined journal fields, or None.

    When public_only=True: public journals always; non-public if viewer owns the
    journal or is subscribed to it (same-URL reuse / private import path).
    """
    uid = _parse_uuid(article_id)
    if uid is None:
        return None

    # Fetch without directory filter so we can apply owner/subscriber exception.
    stmt = (
        select(
            Article,
            Journal.name.label("journal_name"),
            Journal.source_type.label("journal_source_type"),
            Journal.content_type.label("content_type"),
            Journal.directory_status.label("directory_status"),
            Journal.created_by.label("created_by"),
            Journal.id.label("journal_pk"),
        )
        .join(Journal, Article.journal_id == Journal.id)
        .where(Article.id == uid)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None

    (
        article,
        journal_name,
        journal_source_type,
        content_type,
        directory_status,
        created_by,
        journal_pk,
    ) = row
    status = (directory_status or "public").strip().lower()
    if public_only and status != "public":
        viewer = _parse_uuid(viewer_user_id) if viewer_user_id is not None else None
        owner = created_by if isinstance(created_by, UUID) else _parse_uuid(created_by)
        allowed = viewer is not None and owner is not None and viewer == owner
        if not allowed and viewer is not None:
            from app.services import subscriptions as sub_service

            allowed = await sub_service.is_subscribed(session, viewer, journal_pk)
        if not allowed:
            return None

    return _article_out(
        article,
        journal_name=journal_name,
        journal_source_type=journal_source_type,
        content_type=content_type,
    )


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
            Journal.content_type.label("content_type"),
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

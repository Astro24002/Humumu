"""Journal query helpers (public list/get with article stats)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
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


def _health_status(journal: Journal) -> str:
    failures = int(getattr(journal, "consecutive_failures", 0) or 0)
    if not journal.is_active or failures >= 10:
        return "paused"
    return "ok"


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
            "content_type": getattr(journal, "content_type", None) or "journal",
            "directory_status": getattr(journal, "directory_status", None) or "public",
            "homepage_url": getattr(journal, "homepage_url", None) or "",
            "consecutive_failures": int(getattr(journal, "consecutive_failures", 0) or 0),
            "last_error": getattr(journal, "last_error", None),
            "last_success_at": getattr(journal, "last_success_at", None),
            "health_status": _health_status(journal),
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


async def list_journals(
    session: AsyncSession,
    *,
    public_only: bool = True,
    content_type: str | None = None,
    q: str | None = None,
    major: str | None = None,
    minor: str | None = None,
    zone: int | None = None,
    top: bool | None = None,
    year: int | None = None,
) -> list[JournalOut]:
    """List journals ordered by name, with article_count and last_article_date.

    public_only=True (default) restricts to directory_status=public and is_active.
    Admin callers should pass public_only=False.
    Optional CAS filters: major/minor/zone/top/year.
    """
    stats = _stats_subquery()
    stmt = (
        select(
            Journal,
            func.coalesce(stats.c.article_count, 0).label("article_count"),
            stats.c.last_article_date,
        )
        .outerjoin(stats, Journal.id == stats.c.journal_id)
    )
    if public_only:
        stmt = stmt.where(Journal.directory_status == "public").where(
            Journal.is_active.is_(True)
        )
    if content_type:
        stmt = stmt.where(Journal.content_type == content_type)
    if q and q.strip():
        stmt = stmt.where(Journal.name.ilike(f"%{q.strip()}%"))

    # CAS facet filters (no-op when none provided)
    from app.services.categories import journal_ids_for_filters

    cas_ids = await journal_ids_for_filters(
        session, year=year, major=major, minor=minor, zone=zone, top=top
    )
    if cas_ids is not None:
        if not cas_ids:
            return []
        stmt = stmt.where(Journal.id.in_(cas_ids))

    stmt = stmt.order_by(Journal.name)
    result = await session.execute(stmt)
    rows = result.all()
    return [
        _journal_out(row[0], article_count=row[1], last_article_date=row[2])
        for row in rows
    ]


async def get_journal(
    session: AsyncSession,
    journal_id: str | UUID,
    *,
    public_only: bool = True,
) -> JournalOut | None:
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
    if public_only:
        stmt = stmt.where(Journal.directory_status == "public")
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return _journal_out(row[0], article_count=row[1], last_article_date=row[2])


async def find_by_url(session: AsyncSession, source_url: str) -> JournalOut | None:
    """Find journal by normalized or exact source_url (with article stats), or None."""
    from app.services.feed_url import normalize_feed_url

    normalized = normalize_feed_url(source_url) or source_url
    stats = _stats_subquery()
    stmt = (
        select(
            Journal,
            func.coalesce(stats.c.article_count, 0).label("article_count"),
            stats.c.last_article_date,
        )
        .outerjoin(stats, Journal.id == stats.c.journal_id)
        .where(
            (Journal.normalized_source_url == normalized)
            | (Journal.source_url == source_url)
            | (Journal.source_url == normalized)
        )
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
    is_active: bool = True,
    content_type: str = "journal",
    directory_status: str = "public",
    homepage_url: str = "",
) -> JournalOut:
    """Create a journal and return JournalOut (no stats yet)."""
    from app.services.feed_url import normalize_feed_url

    uid = _parse_uuid(created_by) if created_by is not None else None
    normalized = normalize_feed_url(source_url) or None
    journal = Journal(
        name=name,
        slug=slug or slugify(name),
        source_type=source_type or "rss",
        source_url=source_url,
        description=description or "",
        fetch_interval=fetch_interval if fetch_interval is not None else timedelta(minutes=30),
        is_active=is_active,
        created_by=uid,
        content_type=content_type or "journal",
        directory_status=directory_status or "public",
        homepage_url=homepage_url or "",
        normalized_source_url=normalized,
    )
    session.add(journal)
    await session.flush()
    await session.refresh(journal)
    return _journal_out(journal, article_count=0, last_article_date=None)


async def count_journals(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Journal))
    return int(result.scalar_one() or 0)


async def count_pending_requests(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(JournalRequest)
        .where(JournalRequest.status == "pending")
    )
    return int(result.scalar_one() or 0)


async def list_all_journal_requests(session: AsyncSession) -> list[JournalRequestOut]:
    stmt = select(JournalRequest).order_by(JournalRequest.created_at.desc())
    result = await session.execute(stmt)
    return [_request_out(row) for row in result.scalars().all()]


async def update_journal(
    session: AsyncSession,
    journal_id: str | UUID,
    *,
    name: str | None = None,
    slug: str | None = None,
    source_type: str | None = None,
    source_url: str | None = None,
    description: str | None = None,
    fetch_interval: timedelta | None = None,
    is_active: bool | None = None,
    directory_status: str | None = None,
) -> bool:
    """Partial-update a journal. Returns True if a row was updated."""
    uid = _parse_uuid(journal_id)
    if uid is None:
        return False

    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if slug is not None:
        values["slug"] = slug
    if source_type is not None:
        values["source_type"] = source_type
    if source_url is not None:
        values["source_url"] = source_url
    if description is not None:
        values["description"] = description
    if fetch_interval is not None:
        values["fetch_interval"] = fetch_interval
    if is_active is not None:
        values["is_active"] = is_active
    if directory_status is not None:
        values["directory_status"] = directory_status
    if not values:
        return False

    result = await session.execute(update(Journal).where(Journal.id == uid).values(**values))
    return bool(result.rowcount)


_VALID_DIRECTORY_STATUSES = frozenset(
    {"private", "pending_review", "public", "rejected", "hidden"}
)


async def set_directory_status(
    session: AsyncSession,
    journal_id: str | UUID,
    directory_status: str,
) -> bool:
    """Set journal directory_status. Returns True if a row was updated."""
    status = (directory_status or "").strip().lower()
    if status not in _VALID_DIRECTORY_STATUSES:
        raise ValueError(
            "directory_status must be one of: private, pending_review, public, rejected, hidden"
        )
    return await update_journal(session, journal_id, directory_status=status)


async def delete_journal(session: AsyncSession, journal_id: str | UUID) -> bool:
    """Delete a journal by id. Returns True if a row was deleted."""
    uid = _parse_uuid(journal_id)
    if uid is None:
        return False

    result = await session.execute(delete(Journal).where(Journal.id == uid))
    return bool(result.rowcount)


async def update_request_status(
    session: AsyncSession,
    request_id: str | UUID,
    status: str,
) -> bool:
    """Set journal request status and reviewed_at. Returns True if updated."""
    uid = _parse_uuid(request_id)
    if uid is None:
        return False

    result = await session.execute(
        update(JournalRequest)
        .where(JournalRequest.id == uid)
        .values(status=status, reviewed_at=datetime.now(timezone.utc))
    )
    return bool(result.rowcount)


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

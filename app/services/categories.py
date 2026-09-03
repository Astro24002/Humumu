"""CAS journal category helpers."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import CasCategory, CasCategoryYear, JournalCasCategory
from app.schemas.category import CasCategoryOut


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _out(row: CasCategory) -> CasCategoryOut:
    return CasCategoryOut.model_validate(row)


async def list_years(session: AsyncSession) -> list[int]:
    result = await session.execute(
        select(CasCategoryYear.year).order_by(CasCategoryYear.year.desc())
    )
    return [int(y) for y in result.scalars().all()]


async def list_categories(
    session: AsyncSession,
    *,
    year: int | None = None,
    major: str | None = None,
) -> list[CasCategoryOut]:
    stmt = select(CasCategory).order_by(
        CasCategory.year.desc(), CasCategory.major, CasCategory.minor, CasCategory.zone
    )
    if year is not None:
        stmt = stmt.where(CasCategory.year == year)
    if major:
        stmt = stmt.where(CasCategory.major == major.strip())
    result = await session.execute(stmt)
    return [_out(r) for r in result.scalars().all()]


async def ensure_year(session: AsyncSession, year: int) -> None:
    stmt = insert(CasCategoryYear).values(year=int(year)).on_conflict_do_nothing()
    await session.execute(stmt)


async def create_category(
    session: AsyncSession,
    *,
    year: int,
    major: str,
    minor: str,
    zone: int,
    is_top: bool = False,
) -> CasCategoryOut:
    year_i = int(year)
    zone_i = int(zone)
    if zone_i < 1 or zone_i > 4:
        raise ValueError("zone must be between 1 and 4")
    major_s = (major or "").strip()
    minor_s = (minor or "").strip()
    if not major_s or not minor_s:
        raise ValueError("major and minor are required")

    await ensure_year(session, year_i)
    row = CasCategory(
        year=year_i,
        major=major_s,
        minor=minor_s,
        zone=zone_i,
        is_top=bool(is_top),
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return _out(row)


async def attach_categories(
    session: AsyncSession,
    journal_id: str | UUID,
    category_ids: list[str | UUID],
) -> int:
    """Attach categories to journal (idempotent). Returns number of links attempted."""
    jid = _parse_uuid(journal_id)
    if jid is None:
        raise ValueError("invalid journal id")
    n = 0
    for cid in category_ids:
        uid = _parse_uuid(cid)
        if uid is None:
            continue
        stmt = (
            insert(JournalCasCategory)
            .values(journal_id=jid, category_id=uid)
            .on_conflict_do_nothing()
        )
        await session.execute(stmt)
        n += 1
    return n


async def journal_ids_for_filters(
    session: AsyncSession,
    *,
    year: int | None = None,
    major: str | None = None,
    minor: str | None = None,
    zone: int | None = None,
    top: bool | None = None,
) -> list[UUID] | None:
    """
    Return journal ids matching CAS filters, or None if no CAS filters applied.
    """
    has_filter = any(v is not None and v != "" for v in (year, major, minor, zone, top))
    if not has_filter:
        return None

    stmt = (
        select(JournalCasCategory.journal_id)
        .join(CasCategory, CasCategory.id == JournalCasCategory.category_id)
        .distinct()
    )
    if year is not None:
        stmt = stmt.where(CasCategory.year == int(year))
    if major:
        stmt = stmt.where(CasCategory.major == major.strip())
    if minor:
        stmt = stmt.where(CasCategory.minor == minor.strip())
    if zone is not None:
        stmt = stmt.where(CasCategory.zone == int(zone))
    if top is not None:
        stmt = stmt.where(CasCategory.is_top.is_(bool(top)))

    result = await session.execute(stmt)
    return list(result.scalars().all())

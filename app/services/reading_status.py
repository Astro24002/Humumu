"""Per-user article reading status (read / star / later / original click)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_article_status import UserArticleStatus
from app.schemas.reading import ArticleStatusOut


def _parse_uuid(value: str | UUID) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _status_out(row: UserArticleStatus) -> ArticleStatusOut:
    return ArticleStatusOut.model_validate(row)


async def get_status(
    session: AsyncSession,
    user_id: str | UUID,
    article_id: str | UUID,
) -> ArticleStatusOut | None:
    uid = _parse_uuid(user_id)
    aid = _parse_uuid(article_id)
    if uid is None or aid is None:
        return None
    result = await session.execute(
        select(UserArticleStatus).where(
            UserArticleStatus.user_id == uid,
            UserArticleStatus.article_id == aid,
        )
    )
    row = result.scalar_one_or_none()
    return _status_out(row) if row is not None else None


async def upsert_status(
    session: AsyncSession,
    user_id: str | UUID,
    article_id: str | UUID,
    *,
    is_read: bool | None = None,
    is_starred: bool | None = None,
    is_later: bool | None = None,
) -> ArticleStatusOut:
    uid = _parse_uuid(user_id)
    aid = _parse_uuid(article_id)
    if uid is None or aid is None:
        raise ValueError("invalid id")

    values: dict = {
        "user_id": uid,
        "article_id": aid,
        "updated_at": datetime.now(timezone.utc),
    }
    if is_read is not None:
        values["is_read"] = is_read
    if is_starred is not None:
        values["is_starred"] = is_starred
    if is_later is not None:
        values["is_later"] = is_later

    # Ensure defaults on insert when fields omitted
    insert_values = {
        "user_id": uid,
        "article_id": aid,
        "is_read": bool(is_read) if is_read is not None else False,
        "is_starred": bool(is_starred) if is_starred is not None else False,
        "is_later": bool(is_later) if is_later is not None else False,
        "updated_at": datetime.now(timezone.utc),
    }
    update_values = {k: v for k, v in values.items() if k not in ("user_id", "article_id")}
    if not update_values:
        update_values = {"updated_at": datetime.now(timezone.utc)}

    stmt = (
        insert(UserArticleStatus)
        .values(**insert_values)
        .on_conflict_do_update(
            index_elements=["user_id", "article_id"],
            set_=update_values,
        )
        .returning(UserArticleStatus)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    return _status_out(row)


async def mark_original_click(
    session: AsyncSession,
    user_id: str | UUID,
    article_id: str | UUID,
) -> ArticleStatusOut:
    uid = _parse_uuid(user_id)
    aid = _parse_uuid(article_id)
    if uid is None or aid is None:
        raise ValueError("invalid id")

    now = datetime.now(timezone.utc)
    stmt = (
        insert(UserArticleStatus)
        .values(
            user_id=uid,
            article_id=aid,
            is_read=True,
            original_clicked_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "article_id"],
            set_={
                "is_read": True,
                "original_clicked_at": now,
                "updated_at": now,
            },
        )
        .returning(UserArticleStatus)
    )
    result = await session.execute(stmt)
    row = result.scalar_one()
    return _status_out(row)

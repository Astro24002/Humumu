"""Subscription helpers: journals, authors, keywords, notifications."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import Journal
from app.models.notification import Notification
from app.models.subscription import AuthorTracking, JournalSubscription, KeywordSubscription
from app.schemas.journal import JournalOut
from app.schemas.notification import NotificationOut
from app.schemas.subscription import (
    AuthorTrackingOut,
    KeywordSubscriptionOut,
    SubscribedJournalOut,
)
from app.services.journals import _journal_out


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
    if limit < 0:
        return 0
    return limit


async def list_subscribed_journals(
    session: AsyncSession,
    user_id: str | UUID,
) -> list[SubscribedJournalOut]:
    """Active journals the user is subscribed to, with notify prefs, ordered by name."""
    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(Journal, JournalSubscription)
        .join(JournalSubscription, Journal.id == JournalSubscription.journal_id)
        .where(JournalSubscription.user_id == uid, Journal.is_active.is_(True))
        .order_by(Journal.name)
    )
    result = await session.execute(stmt)
    rows = result.all()
    out: list[SubscribedJournalOut] = []
    for journal, sub in rows:
        base = _journal_out(journal, article_count=0, last_article_date=None)
        out.append(
            SubscribedJournalOut(
                **base.model_dump(),
                push_frequency=(sub.push_frequency or "default"),
                email_enabled=bool(sub.email_enabled if sub.email_enabled is not None else True),
                wechat_enabled=bool(sub.wechat_enabled if sub.wechat_enabled is not None else True),
            )
        )
    return out


async def journal_exists(session: AsyncSession, journal_id: str | UUID) -> bool:
    """True if a journal row exists (any directory_status). Prefer can_subscribe."""
    uid = _parse_uuid(journal_id)
    if uid is None:
        return False
    result = await session.execute(select(Journal.id).where(Journal.id == uid))
    return result.scalar_one_or_none() is not None


async def can_subscribe(
    session: AsyncSession,
    user_id: str | UUID,
    journal_id: str | UUID,
) -> bool:
    """Subscribe allowed for public directory journals, or journals created by user.

    Non-public sources are not discoverable; strangers must not subscribe by UUID.
    """
    uid = _parse_uuid(user_id)
    jid = _parse_uuid(journal_id)
    if uid is None or jid is None:
        return False
    result = await session.execute(
        select(Journal.directory_status, Journal.created_by).where(Journal.id == jid)
    )
    row = result.one_or_none()
    if row is None:
        return False
    status, created_by = row[0], row[1]
    status_s = (status or "public").strip().lower()
    if status_s == "public":
        return True
    owner = created_by if isinstance(created_by, UUID) else _parse_uuid(created_by)
    return owner is not None and owner == uid


async def subscribe_journal(
    session: AsyncSession,
    user_id: str | UUID,
    journal_id: str | UUID,
) -> None:
    """INSERT ON CONFLICT DO NOTHING for journal subscription."""
    uid = _parse_uuid(user_id)
    jid = _parse_uuid(journal_id)
    if uid is None or jid is None:
        raise ValueError("invalid id")

    stmt = (
        insert(JournalSubscription)
        .values(user_id=uid, journal_id=jid)
        .on_conflict_do_nothing()
    )
    await session.execute(stmt)


async def unsubscribe_journal(
    session: AsyncSession,
    user_id: str | UUID,
    journal_id: str | UUID,
) -> None:
    uid = _parse_uuid(user_id)
    jid = _parse_uuid(journal_id)
    if uid is None or jid is None:
        return

    stmt = delete(JournalSubscription).where(
        JournalSubscription.user_id == uid,
        JournalSubscription.journal_id == jid,
    )
    await session.execute(stmt)


_VALID_SUB_FREQUENCIES = frozenset({"default", "realtime", "daily"})


async def update_journal_subscription(
    session: AsyncSession,
    user_id: str | UUID,
    journal_id: str | UUID,
    *,
    push_frequency: str | None = None,
    email_enabled: bool | None = None,
    wechat_enabled: bool | None = None,
) -> bool:
    """Update per-subscription notify prefs. Returns True if a row was updated."""
    from sqlalchemy import update

    uid = _parse_uuid(user_id)
    jid = _parse_uuid(journal_id)
    if uid is None or jid is None:
        return False

    values: dict = {}
    if push_frequency is not None:
        freq = push_frequency.strip().lower()
        if freq not in _VALID_SUB_FREQUENCIES:
            raise ValueError("push_frequency must be one of: default, realtime, daily")
        values["push_frequency"] = freq
    if email_enabled is not None:
        values["email_enabled"] = bool(email_enabled)
    if wechat_enabled is not None:
        values["wechat_enabled"] = bool(wechat_enabled)
    if not values:
        return False

    result = await session.execute(
        update(JournalSubscription)
        .where(
            JournalSubscription.user_id == uid,
            JournalSubscription.journal_id == jid,
        )
        .values(**values)
    )
    return bool(result.rowcount)


async def get_journal_subscription(
    session: AsyncSession,
    user_id: str | UUID,
    journal_id: str | UUID,
):
    """Return JournalSubscription row or None."""
    uid = _parse_uuid(user_id)
    jid = _parse_uuid(journal_id)
    if uid is None or jid is None:
        return None
    result = await session.execute(
        select(JournalSubscription).where(
            JournalSubscription.user_id == uid,
            JournalSubscription.journal_id == jid,
        )
    )
    return result.scalar_one_or_none()


async def list_authors(
    session: AsyncSession,
    user_id: str | UUID,
) -> list[AuthorTrackingOut]:
    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(AuthorTracking)
        .where(AuthorTracking.user_id == uid)
        .order_by(AuthorTracking.created_at.desc())
    )
    result = await session.execute(stmt)
    return [AuthorTrackingOut.model_validate(row) for row in result.scalars().all()]


async def add_author(
    session: AsyncSession,
    user_id: str | UUID,
    author_name: str,
) -> None:
    uid = _parse_uuid(user_id)
    if uid is None:
        raise ValueError("invalid user id")

    stmt = (
        insert(AuthorTracking)
        .values(user_id=uid, author_name=author_name)
        .on_conflict_do_nothing()
    )
    await session.execute(stmt)


async def remove_author(
    session: AsyncSession,
    author_id: str | UUID,
    user_id: str | UUID,
) -> None:
    aid = _parse_uuid(author_id)
    uid = _parse_uuid(user_id)
    if aid is None or uid is None:
        return

    stmt = delete(AuthorTracking).where(
        AuthorTracking.id == aid,
        AuthorTracking.user_id == uid,
    )
    await session.execute(stmt)


async def list_keywords(
    session: AsyncSession,
    user_id: str | UUID,
) -> list[KeywordSubscriptionOut]:
    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(KeywordSubscription)
        .where(KeywordSubscription.user_id == uid)
        .order_by(KeywordSubscription.created_at.desc())
    )
    result = await session.execute(stmt)
    return [KeywordSubscriptionOut.model_validate(row) for row in result.scalars().all()]


async def add_keyword(
    session: AsyncSession,
    user_id: str | UUID,
    keyword: str,
) -> None:
    uid = _parse_uuid(user_id)
    if uid is None:
        raise ValueError("invalid user id")

    stmt = (
        insert(KeywordSubscription)
        .values(user_id=uid, keyword=keyword)
        .on_conflict_do_nothing()
    )
    await session.execute(stmt)


async def remove_keyword(
    session: AsyncSession,
    keyword_id: str | UUID,
    user_id: str | UUID,
) -> None:
    kid = _parse_uuid(keyword_id)
    uid = _parse_uuid(user_id)
    if kid is None or uid is None:
        return

    stmt = delete(KeywordSubscription).where(
        KeywordSubscription.id == kid,
        KeywordSubscription.user_id == uid,
    )
    await session.execute(stmt)


async def list_notifications(
    session: AsyncSession,
    user_id: str | UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[NotificationOut]:
    limit = _clamp_limit(limit)
    if offset < 0:
        offset = 0

    uid = _parse_uuid(user_id)
    if uid is None:
        return []

    stmt = (
        select(Notification)
        .where(Notification.user_id == uid)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return [NotificationOut.model_validate(row) for row in result.scalars().all()]

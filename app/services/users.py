from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

VALID_PUSH_FREQUENCIES = frozenset({"realtime", "daily"})


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID | str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_by_wechat_openid(session: AsyncSession, openid: str) -> User | None:
    result = await session.execute(select(User).where(User.wechat_openid == openid))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    password_hash: str,
    name: str = "",
    *,
    wechat_openid: str | None = None,
    push_frequency: str = "daily",
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        name=name or "",
        wechat_openid=wechat_openid,
        push_frequency=push_frequency,
    )
    session.add(user)
    await session.flush()
    return user


async def link_wechat(
    session: AsyncSession,
    user_id: UUID | str,
    openid: str,
) -> bool:
    """Link a WeChat openid to an existing user. Returns True if a row was updated."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            wechat_openid=openid,
            updated_at=datetime.now(timezone.utc),
        )
    )
    return bool(result.rowcount)


async def bind_email(
    session: AsyncSession,
    user_id: UUID | str,
    email: str,
    password_hash: str,
) -> User | None:
    """Attach a real email + password to an existing user (e.g. WeChat stub).

    Caller must ensure the email is not taken and the user is eligible.
    Returns the refreshed user, or None if the user row is missing.
    """
    user = await get_by_id(session, user_id)
    if user is None:
        return None
    user.email = email
    user.password_hash = password_hash
    user.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(user)
    return user


async def get_template_setting(session: AsyncSession, user_id: UUID | str) -> bool:
    """Return wechat_template_subscribed for user; False if user missing."""
    result = await session.execute(
        select(User.wechat_template_subscribed).where(User.id == user_id)
    )
    value = result.scalar_one_or_none()
    return bool(value) if value is not None else False


async def update_template_setting(
    session: AsyncSession,
    user_id: UUID | str,
    subscribed: bool,
) -> bool:
    """Update wechat_template_subscribed. Returns True if a row was updated."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            wechat_template_subscribed=subscribed,
            updated_at=datetime.now(timezone.utc),
        )
    )
    return bool(result.rowcount)


async def update_push_frequency(
    session: AsyncSession,
    user_id: UUID | str,
    push_frequency: str,
) -> bool:
    """Update user push_frequency. Returns True if a row was updated."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            push_frequency=push_frequency,
            updated_at=datetime.now(timezone.utc),
        )
    )
    return bool(result.rowcount)


_WECHAT_STUB_SUFFIX = "%@wechat.user"


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one() or 0)


async def count_stub_users(session: AsyncSession) -> int:
    """Accounts whose email is the WeChat placeholder (`*@wechat.user`)."""
    result = await session.execute(
        select(func.count())
        .select_from(User)
        .where(User.email.ilike(_WECHAT_STUB_SUFFIX))
    )
    return int(result.scalar_one() or 0)


async def count_wechat_unbound(session: AsyncSession) -> int:
    """Accounts with no wechat_openid (email-first users who have not bound mini)."""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.wechat_openid.is_(None))
    )
    return int(result.scalar_one() or 0)


async def list_all_users(
    session: AsyncSession,
    *,
    q: str | None = None,
    has_email: bool | None = None,
    wechat_bound: bool | None = None,
    is_admin: bool | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[User], int]:
    """Return (users, total_matching). Optional q matches email/name (ilike)."""
    if offset < 0:
        offset = 0
    if limit is not None:
        if limit > 200:
            limit = 200
        if limit < 1:
            limit = 1

    conditions = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append(or_(User.email.ilike(term), User.name.ilike(term)))
    if has_email is True:
        conditions.append(~User.email.ilike(_WECHAT_STUB_SUFFIX))
    elif has_email is False:
        conditions.append(User.email.ilike(_WECHAT_STUB_SUFFIX))
    if wechat_bound is True:
        conditions.append(User.wechat_openid.is_not(None))
    elif wechat_bound is False:
        conditions.append(User.wechat_openid.is_(None))
    if is_admin is True:
        conditions.append(User.is_admin.is_(True))
    elif is_admin is False:
        conditions.append(User.is_admin.is_(False))

    count_stmt = select(func.count()).select_from(User)
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)

    stmt = select(User).order_by(User.created_at.desc())
    if conditions:
        stmt = stmt.where(*conditions)
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all()), total


async def set_admin(
    session: AsyncSession,
    user_id: UUID | str,
    is_admin: bool,
) -> User | None:
    """Set users.is_admin. Returns the updated user, or None if missing."""
    user = await get_by_id(session, user_id)
    if user is None:
        return None
    user.is_admin = bool(is_admin)
    user.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(user)
    return user

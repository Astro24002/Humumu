from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
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
    push_frequency: str = "realtime",
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


async def count_users(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(User))
    return int(result.scalar_one() or 0)


async def list_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

VALID_PUSH_FREQUENCIES = frozenset({"realtime", "daily"})


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: UUID | str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    email: str,
    password_hash: str,
    name: str = "",
) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        name=name or "",
    )
    session.add(user)
    await session.flush()
    return user


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

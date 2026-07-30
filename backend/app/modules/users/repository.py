from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


async def lock_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(
        select(User).where(User.id == user_id).with_for_update()
    )


async def list_users_by_ids(session: AsyncSession, user_ids: list[UUID]) -> list[User]:
    if not user_ids:
        return []
    return list(await session.scalars(select(User).where(User.id.in_(user_ids))))


async def list_due_for_refill(
    session: AsyncSession, cutoff: datetime
) -> list[User]:
    return list(
        await session.scalars(
            select(User)
            .where(
                (User.last_refill_at.is_(None))
                | (User.last_refill_at <= cutoff)
            )
            .with_for_update(skip_locked=True)
        )
    )


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    display_name: str,
    password_hash: str,
) -> User:
    user = User(
        email=email.lower(),
        display_name=display_name.strip(),
        password_hash=password_hash,
    )
    session.add(user)
    await session.flush()
    return user

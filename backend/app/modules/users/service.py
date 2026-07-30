from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ledger.service import get_balance
from app.modules.users.models import User
from app.modules.users.repository import (
    list_due_for_refill as repository_list_due_for_refill,
)
from app.modules.users.repository import list_users_by_ids as repository_list_users_by_ids
from app.modules.users.repository import lock_user as repository_lock_user


async def get_profile(session: AsyncSession, user: User) -> tuple[User, Decimal]:
    return user, await get_balance(session, user.id)


async def lock_user(session: AsyncSession, user_id: UUID) -> User:
    user = await repository_lock_user(session, user_id)
    if user is None:
        raise LookupError("user not found")
    return user


async def list_users_by_ids(session: AsyncSession, user_ids: list[UUID]) -> list[User]:
    return await repository_list_users_by_ids(session, user_ids)


async def list_due_for_refill(session: AsyncSession, cutoff: datetime) -> list[User]:
    return await repository_list_due_for_refill(session, cutoff)

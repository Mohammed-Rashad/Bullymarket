from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ledger.service import get_balance
from app.modules.users.models import User
from app.modules.users.repository import lock_user as repository_lock_user


async def get_profile(session: AsyncSession, user: User) -> tuple[User, Decimal]:
    return user, await get_balance(session, user.id)


async def lock_user(session: AsyncSession, user_id: UUID) -> User:
    user = await repository_lock_user(session, user_id)
    if user is None:
        raise LookupError("user not found")
    return user

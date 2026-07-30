from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ledger.models import LedgerEntry, LedgerEntryType


async def add_entry(
    session: AsyncSession,
    *,
    user_id: UUID,
    amount: Decimal,
    entry_type: LedgerEntryType,
    bet_id: UUID | None = None,
    related_ledger_entry_id: UUID | None = None,
) -> LedgerEntry:
    entry = LedgerEntry(
        user_id=user_id,
        amount=amount,
        entry_type=entry_type,
        bet_id=bet_id,
        related_ledger_entry_id=related_ledger_entry_id,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_balance(session: AsyncSession, user_id: UUID) -> Decimal:
    statement = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
        LedgerEntry.user_id == user_id
    )
    value = await session.scalar(statement)
    return Decimal(value or 0)

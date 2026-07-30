from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ledger import repository
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
    return await repository.add_entry(
        session,
        user_id=user_id,
        amount=amount,
        entry_type=entry_type,
        bet_id=bet_id,
        related_ledger_entry_id=related_ledger_entry_id,
    )


async def get_balance(session: AsyncSession, user_id: UUID) -> Decimal:
    return await repository.get_balance(session, user_id)


async def get_bet_stakes(
    session: AsyncSession, bet_id: UUID
) -> list[tuple[UUID, Decimal]]:
    return await repository.get_bet_stakes(session, bet_id)


async def get_unreversed_payouts(
    session: AsyncSession, bet_id: UUID
) -> list[LedgerEntry]:
    return await repository.get_unreversed_payouts(session, bet_id)


async def get_net_results(
    session: AsyncSession, bet_ids: list[UUID]
) -> list[tuple[UUID, Decimal]]:
    return await repository.get_net_results(session, bet_ids)

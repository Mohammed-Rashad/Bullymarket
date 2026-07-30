from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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


async def get_bet_stakes(
    session: AsyncSession, bet_id: UUID
) -> list[tuple[UUID, Decimal]]:
    rows = await session.execute(
        select(
            LedgerEntry.user_id,
            -func.sum(LedgerEntry.amount),
        )
        .where(
            LedgerEntry.bet_id == bet_id,
            LedgerEntry.entry_type == LedgerEntryType.BET_PLACED,
        )
        .group_by(LedgerEntry.user_id)
    )
    return [(user_id, Decimal(amount)) for user_id, amount in rows.tuples()]


async def get_unreversed_payouts(
    session: AsyncSession, bet_id: UUID
) -> list[LedgerEntry]:
    reversal = aliased(LedgerEntry)
    return list(
        await session.scalars(
            select(LedgerEntry)
            .outerjoin(
                reversal,
                and_(
                    reversal.related_ledger_entry_id == LedgerEntry.id,
                    reversal.entry_type == LedgerEntryType.RESOLUTION_REVERSAL,
                ),
            )
            .where(
                LedgerEntry.bet_id == bet_id,
                LedgerEntry.entry_type == LedgerEntryType.PAYOUT,
                reversal.id.is_(None),
            )
        )
    )


async def get_net_results(
    session: AsyncSession, bet_ids: list[UUID]
) -> list[tuple[UUID, Decimal]]:
    if not bet_ids:
        return []
    rows = await session.execute(
        select(LedgerEntry.user_id, func.sum(LedgerEntry.amount))
        .where(
            LedgerEntry.bet_id.in_(bet_ids),
            LedgerEntry.entry_type.in_(
                [
                    LedgerEntryType.BET_PLACED,
                    LedgerEntryType.PAYOUT,
                    LedgerEntryType.RESOLUTION_REVERSAL,
                ]
            ),
        )
        .group_by(LedgerEntry.user_id)
    )
    return [(user_id, Decimal(amount)) for user_id, amount in rows.tuples()]

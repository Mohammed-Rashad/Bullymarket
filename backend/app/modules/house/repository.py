from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bets.models import Bet, PricingMethod
from app.modules.house.models import HouseLedgerEntry, HouseLedgerEntryType
from app.modules.trading.models import Trade


async def add_entry(
    session: AsyncSession,
    *,
    bet_id: UUID,
    group_id: UUID | None,
    entry_type: HouseLedgerEntryType,
    cash_delta: Decimal,
    reserve_delta: Decimal,
    realized_pnl_delta: Decimal,
    trade_id: UUID | None,
) -> HouseLedgerEntry:
    value = await session.scalar(
        select(func.coalesce(func.max(HouseLedgerEntry.sequence), 0)).where(
            HouseLedgerEntry.bet_id == bet_id
        )
    )
    entry = HouseLedgerEntry(
        bet_id=bet_id,
        group_id=group_id,
        trade_id=trade_id,
        sequence=int(value or 0) + 1,
        entry_type=entry_type,
        cash_delta=cash_delta,
        reserve_delta=reserve_delta,
        realized_pnl_delta=realized_pnl_delta,
    )
    session.add(entry)
    await session.flush()
    return entry


async def list_entries(session: AsyncSession, bet_id: UUID) -> list[HouseLedgerEntry]:
    return list(
        await session.scalars(
            select(HouseLedgerEntry)
            .where(HouseLedgerEntry.bet_id == bet_id)
            .order_by(HouseLedgerEntry.sequence)
        )
    )


async def list_lmsr_bets(
    session: AsyncSession,
    *,
    bet_id: UUID | None = None,
    group_id: UUID | None = None,
) -> list[Bet]:
    statement = select(Bet).where(Bet.pricing_method == PricingMethod.LMSR)
    if bet_id is not None:
        statement = statement.where(Bet.id == bet_id)
    elif group_id is not None:
        statement = statement.where(Bet.group_id == group_id)
    return list(await session.scalars(statement))


async def trade_count_and_cash_flow(
    session: AsyncSession,
    *,
    bet_ids: list[UUID],
) -> tuple[int, Decimal]:
    if not bet_ids:
        return 0, Decimal(0)
    row = (
        await session.execute(
            select(
                func.count(Trade.id),
                func.coalesce(func.sum(Trade.house_cash_flow), 0),
            ).where(Trade.bet_id.in_(bet_ids))
        )
    ).one()
    return int(row[0]), Decimal(row[1])

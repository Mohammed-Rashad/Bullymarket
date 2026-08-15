from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bets.models import BetStatus
from app.modules.house import repository
from app.modules.house.models import HouseLedgerEntry, HouseLedgerEntryType
from app.modules.house.schemas import HouseSummaryResponse


async def add_house_entry(
    session: AsyncSession,
    *,
    bet_id: UUID,
    group_id: UUID | None,
    entry_type: HouseLedgerEntryType,
    cash_delta: Decimal = Decimal(0),
    reserve_delta: Decimal = Decimal(0),
    realized_pnl_delta: Decimal = Decimal(0),
    trade_id: UUID | None = None,
) -> HouseLedgerEntry:
    if cash_delta == 0 and reserve_delta == 0 and realized_pnl_delta == 0:
        raise ValueError("a house ledger entry must have a financial effect")
    return await repository.add_entry(
        session,
        bet_id=bet_id,
        group_id=group_id,
        entry_type=entry_type,
        cash_delta=cash_delta,
        reserve_delta=reserve_delta,
        realized_pnl_delta=realized_pnl_delta,
        trade_id=trade_id,
    )


async def get_summary(
    session: AsyncSession,
    *,
    bet_id: UUID | None = None,
    group_id: UUID | None = None,
) -> HouseSummaryResponse:
    bets = await repository.list_lmsr_bets(
        session,
        bet_id=bet_id,
        group_id=group_id,
    )
    trade_count, trade_cash_flow = await repository.trade_count_and_cash_flow(
        session,
        bet_ids=[bet.id for bet in bets],
    )
    unsettled = [
        bet for bet in bets if bet.status in {BetStatus.OPEN, BetStatus.CLOSED}
    ]
    if bet_id is not None:
        scope: Literal["bet", "group", "global"] = "bet"
    elif group_id is not None:
        scope = "group"
    else:
        scope = "global"
    return HouseSummaryResponse(
        scope=scope,
        bet_id=bet_id,
        group_id=group_id,
        markets=len(bets),
        open_markets=len(unsettled),
        trades=trade_count,
        reserved_exposure=sum(
            (bet.house_reserve for bet in unsettled),
            start=Decimal(0),
        ),
        trade_cash_flow=trade_cash_flow,
        current_cash_balance=sum(
            (bet.house_cash_balance for bet in bets),
            start=Decimal(0),
        ),
        realized_profit_loss=sum(
            (
                bet.house_profit_loss
                for bet in bets
                if bet.house_profit_loss is not None
            ),
            start=Decimal(0),
        ),
    )

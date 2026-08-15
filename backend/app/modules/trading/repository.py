from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.models import Position, Trade


async def get_position(
    session: AsyncSession,
    *,
    user_id: UUID,
    bet_id: UUID,
    outcome_id: UUID,
    lock: bool = False,
) -> Position | None:
    statement = select(Position).where(
        Position.user_id == user_id,
        Position.bet_id == bet_id,
        Position.outcome_id == outcome_id,
    )
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def has_position(session: AsyncSession, *, user_id: UUID, bet_id: UUID) -> bool:
    return (
        await session.scalar(
            select(Position.id)
            .where(
                Position.user_id == user_id,
                Position.bet_id == bet_id,
            )
            .limit(1)
        )
        is not None
    )


async def list_user_positions(
    session: AsyncSession, *, user_id: UUID, bet_id: UUID
) -> list[Position]:
    return list(
        await session.scalars(
            select(Position)
            .where(
                Position.user_id == user_id,
                Position.bet_id == bet_id,
            )
            .order_by(Position.created_at)
        )
    )


async def list_outcome_positions(
    session: AsyncSession, *, bet_id: UUID, outcome_id: UUID
) -> list[Position]:
    return list(
        await session.scalars(
            select(Position).where(
                Position.bet_id == bet_id,
                Position.outcome_id == outcome_id,
            )
        )
    )


async def has_position_in_bets(
    session: AsyncSession, *, user_id: UUID, bet_ids: list[UUID]
) -> bool:
    if not bet_ids:
        return False
    return (
        await session.scalar(
            select(Position.id)
            .where(
                Position.user_id == user_id,
                Position.bet_id.in_(bet_ids),
            )
            .limit(1)
        )
        is not None
    )


async def add_trade(session: AsyncSession, trade: Trade) -> Trade:
    session.add(trade)
    await session.flush()
    return trade


async def next_trade_sequence(session: AsyncSession, bet_id: UUID) -> int:
    value = await session.scalar(
        select(func.coalesce(func.max(Trade.sequence), 0)).where(Trade.bet_id == bet_id)
    )
    return int(value or 0) + 1


async def list_trades(session: AsyncSession, bet_id: UUID) -> list[Trade]:
    return list(
        await session.scalars(
            select(Trade)
            .where(Trade.bet_id == bet_id)
            .order_by(Trade.sequence)
        )
    )


async def total_trade_cost(session: AsyncSession, bet_id: UUID) -> Decimal:
    value = await session.scalar(
        select(func.coalesce(func.sum(Trade.cost), 0)).where(Trade.bet_id == bet_id)
    )
    return Decimal(value or 0)

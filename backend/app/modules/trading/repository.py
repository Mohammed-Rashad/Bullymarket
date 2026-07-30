from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trading.models import Position


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

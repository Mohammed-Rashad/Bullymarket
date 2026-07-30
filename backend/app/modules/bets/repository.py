from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bets.models import (
    Bet,
    BetEditEvent,
    BetEditType,
    BetStatus,
    BetVisibility,
    BetVisibilityOverride,
    Outcome,
)


async def create_bet(
    session: AsyncSession,
    *,
    group_id: UUID | None,
    created_by: UUID,
    question: str,
    description: str | None,
    visibility: BetVisibility,
    end_time: datetime,
    outcome_labels: list[str],
    liquidity_seed: Decimal,
    visible_to_user_ids: list[UUID] | None,
) -> tuple[Bet, list[Outcome]]:
    bet = Bet(
        group_id=group_id,
        created_by=created_by,
        question=question.strip(),
        description=description,
        visibility=visibility,
        status=BetStatus.OPEN,
        end_time=end_time,
        liquidity_seed=liquidity_seed,
    )
    session.add(bet)
    await session.flush()
    outcomes = [
        Outcome(
            bet_id=bet.id,
            label=label,
            pool_shares=liquidity_seed,
            display_order=index,
        )
        for index, label in enumerate(outcome_labels)
    ]
    session.add_all(outcomes)
    if group_id is not None and visible_to_user_ids:
        session.add_all(
            BetVisibilityOverride(
                bet_id=bet.id,
                group_id=group_id,
                user_id=user_id,
            )
            for user_id in set(visible_to_user_ids)
        )
    await session.flush()
    return bet, outcomes


async def get_bet(
    session: AsyncSession, bet_id: UUID, *, lock: bool = False
) -> Bet | None:
    statement = select(Bet).where(Bet.id == bet_id)
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def get_outcomes(
    session: AsyncSession, bet_id: UUID, *, lock: bool = False
) -> list[Outcome]:
    statement = (
        select(Outcome)
        .where(Outcome.bet_id == bet_id)
        .order_by(Outcome.display_order)
    )
    if lock:
        statement = statement.with_for_update()
    return list(await session.scalars(statement))


async def get_outcome(
    session: AsyncSession, bet_id: UUID, outcome_id: UUID
) -> Outcome | None:
    return await session.scalar(
        select(Outcome).where(
            Outcome.id == outcome_id,
            Outcome.bet_id == bet_id,
        )
    )


async def list_group_bets(session: AsyncSession, group_id: UUID) -> list[Bet]:
    return list(
        await session.scalars(
            select(Bet)
            .where(
                Bet.group_id == group_id,
                Bet.visibility == BetVisibility.GROUP,
                Bet.status != BetStatus.CANCELLED,
            )
            .order_by(Bet.created_at.desc())
        )
    )


async def list_public_bets(session: AsyncSession) -> list[Bet]:
    return list(
        await session.scalars(
            select(Bet)
            .where(
                Bet.group_id.is_(None),
                Bet.visibility == BetVisibility.PUBLIC,
                Bet.status != BetStatus.CANCELLED,
            )
            .order_by(Bet.created_at.desc())
        )
    )


async def get_visibility_user_ids(session: AsyncSession, bet_id: UUID) -> set[UUID]:
    return set(
        await session.scalars(
            select(BetVisibilityOverride.user_id).where(
                BetVisibilityOverride.bet_id == bet_id
            )
        )
    )


async def add_edit_event(
    session: AsyncSession,
    *,
    bet_id: UUID,
    edited_by: UUID,
    old_end_time: datetime,
    new_end_time: datetime,
) -> BetEditEvent:
    event = BetEditEvent(
        bet_id=bet_id,
        edited_by=edited_by,
        edit_type=BetEditType.END_TIME,
        old_value=old_end_time.isoformat(),
        new_value=new_end_time.isoformat(),
    )
    session.add(event)
    await session.flush()
    return event


async def list_edit_events(session: AsyncSession, bet_id: UUID) -> list[BetEditEvent]:
    return list(
        await session.scalars(
            select(BetEditEvent)
            .where(BetEditEvent.bet_id == bet_id)
            .order_by(BetEditEvent.created_at)
        )
    )


async def list_resolved_bet_ids(
    session: AsyncSession,
    *,
    group_id: UUID | None,
    public: bool,
    resolved_since: datetime | None,
) -> list[UUID]:
    predicates = [Bet.status == BetStatus.RESOLVED]
    if public:
        predicates.extend(
            [Bet.visibility == BetVisibility.PUBLIC, Bet.group_id.is_(None)]
        )
    else:
        predicates.extend(
            [Bet.visibility == BetVisibility.GROUP, Bet.group_id == group_id]
        )
    if resolved_since is not None:
        predicates.append(Bet.resolved_at >= resolved_since)
    return list(await session.scalars(select(Bet.id).where(*predicates)))


async def list_unsettled_group_bet_ids(
    session: AsyncSession, group_id: UUID
) -> list[UUID]:
    return list(
        await session.scalars(
            select(Bet.id).where(
                Bet.group_id == group_id,
                Bet.visibility == BetVisibility.GROUP,
                Bet.status.in_([BetStatus.OPEN, BetStatus.CLOSED]),
            )
        )
    )


async def count_bets(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Bet)) or 0)

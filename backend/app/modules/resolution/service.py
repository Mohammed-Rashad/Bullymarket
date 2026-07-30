import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.core.logging import business_event
from app.modules.bets import repository as bets_repository
from app.modules.bets.models import BetStatus, BetVisibility
from app.modules.bets.service import aware, refresh_time_status
from app.modules.groups.service import require_admin
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry, get_unreversed_payouts
from app.modules.resolution import repository
from app.modules.resolution.models import ResolutionEvent
from app.modules.resolution.schemas import ResolutionResponse
from app.modules.trading.service import list_outcome_positions, money

logger = logging.getLogger(__name__)


async def resolve_bet(
    session: AsyncSession,
    *,
    bet_id: UUID,
    outcome_id: UUID,
    resolver_id: UUID,
) -> ResolutionResponse:
    bet = await bets_repository.get_bet(session, bet_id, lock=True)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    if bet.visibility is BetVisibility.GROUP:
        if bet.group_id is None:
            raise DomainError("invalid_market", "Group bet has no group", 500)
        await require_admin(session, bet.group_id, resolver_id)

    outcome = await bets_repository.get_outcome(session, bet.id, outcome_id)
    if outcome is None:
        raise DomainError("outcome_not_found", "Outcome does not belong to this bet", 404)
    if bet.status is BetStatus.CANCELLED:
        raise DomainError("bet_cancelled", "A cancelled bet cannot be resolved", 409)

    now = datetime.now(UTC)
    refresh_time_status(bet, now=now)
    is_correction = bet.status is BetStatus.RESOLVED
    if not is_correction and aware(bet.end_time) > now:
        raise DomainError("bet_still_open", "The bet cannot be resolved before its end time", 409)
    if is_correction and bet.resolved_outcome_id == outcome_id:
        raise DomainError(
            "outcome_unchanged",
            "Choose a different outcome when correcting a resolution",
            409,
        )

    if is_correction:
        for payout in await get_unreversed_payouts(session, bet.id):
            await add_entry(
                session,
                user_id=payout.user_id,
                amount=-payout.amount,
                entry_type=LedgerEntryType.RESOLUTION_REVERSAL,
                bet_id=bet.id,
                related_ledger_entry_id=payout.id,
            )

    positions = await list_outcome_positions(
        session,
        bet_id=bet.id,
        outcome_id=outcome_id,
    )
    total_payout = Decimal(0)
    for position in positions:
        payout_amount = money(position.shares)
        if payout_amount <= 0:
            continue
        await add_entry(
            session,
            user_id=position.user_id,
            amount=payout_amount,
            entry_type=LedgerEntryType.PAYOUT,
            bet_id=bet.id,
        )
        total_payout += payout_amount

    if bet.resolved_at is None:
        bet.resolved_at = now
    bet.status = BetStatus.RESOLVED
    bet.resolved_outcome_id = outcome_id
    bet.resolved_by = resolver_id
    await repository.add_event(
        session,
        ResolutionEvent(
            bet_id=bet.id,
            outcome_id=outcome_id,
            resolved_by=resolver_id,
            is_correction=is_correction,
        ),
    )
    await session.flush()
    business_event(
        logger,
        "bet_resolution_corrected" if is_correction else "bet_resolved",
        bet_id=str(bet.id),
        outcome_id=str(outcome_id),
        resolver_id=str(resolver_id),
        affected_users=len(positions),
        total_payout=str(money(total_payout)),
    )
    return ResolutionResponse(
        bet_id=bet.id,
        outcome_id=outcome_id,
        is_correction=is_correction,
        affected_users=len(positions),
        total_payout=money(total_payout),
        resolved_at=bet.resolved_at,
    )


async def list_resolution_events(
    session: AsyncSession, *, bet_id: UUID, user_id: UUID
) -> list[ResolutionEvent]:
    from app.modules.bets.service import get_visible_bet

    await get_visible_bet(session, bet_id=bet_id, user_id=user_id)
    return await repository.list_events(session, bet_id)


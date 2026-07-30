import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.logging import business_event
from app.modules.amm import get_prices
from app.modules.bets import repository
from app.modules.bets.models import Bet, BetStatus, BetVisibility, Outcome
from app.modules.bets.schemas import (
    BetResponse,
    CancellationResponse,
    CreateBetRequest,
    OutcomeResponse,
)
from app.modules.groups.models import MemberRole, MembershipStatus
from app.modules.groups.service import (
    get_membership_state,
    require_admin,
    require_membership,
)
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry, get_bet_stakes

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def refresh_time_status(bet: Bet, *, now: datetime | None = None) -> None:
    if bet.status is BetStatus.OPEN and aware(bet.end_time) <= (now or utc_now()):
        bet.status = BetStatus.CLOSED


async def build_response(
    session: AsyncSession,
    bet: Bet,
    outcomes: list[Outcome] | None = None,
) -> BetResponse:
    refresh_time_status(bet)
    market_outcomes = outcomes or await repository.get_outcomes(session, bet.id)
    if len(market_outcomes) != 2:
        raise DomainError("invalid_market", "A v1 market must have exactly two outcomes", 500)
    prices = get_prices(market_outcomes[0].pool_shares, market_outcomes[1].pool_shares)
    return BetResponse(
        id=bet.id,
        group_id=bet.group_id,
        created_by=bet.created_by,
        question=bet.question,
        description=bet.description,
        visibility=bet.visibility,
        status=bet.status,
        end_time=bet.end_time,
        resolved_outcome_id=bet.resolved_outcome_id,
        resolved_at=bet.resolved_at,
        created_at=bet.created_at,
        outcomes=[
            OutcomeResponse(
                id=outcome.id,
                label=outcome.label,
                display_order=outcome.display_order,
                pool_shares=outcome.pool_shares,
                price=prices.yes if outcome.display_order == 0 else prices.no,
            )
            for outcome in market_outcomes
        ],
    )


async def _visibility_allows(
    session: AsyncSession,
    *,
    bet: Bet,
    user_id: UUID,
    member_role: MemberRole,
) -> bool:
    if bet.created_by == user_id or member_role is MemberRole.ADMIN:
        return True
    allowed_ids = await repository.get_visibility_user_ids(session, bet.id)
    return not allowed_ids or user_id in allowed_ids


async def create_group_bet(
    session: AsyncSession,
    *,
    group_id: UUID,
    creator_id: UUID,
    payload: CreateBetRequest,
    settings: Settings,
) -> BetResponse:
    await require_membership(session, group_id, creator_id)
    if aware(payload.end_time) <= utc_now():
        raise DomainError("invalid_end_time", "Bet end time must be in the future")
    if payload.visible_to_user_ids:
        for user_id in set(payload.visible_to_user_ids):
            membership = await get_membership_state(session, group_id, user_id)
            if membership is None or membership.status is not MembershipStatus.ACTIVE:
                raise DomainError(
                    "invalid_visibility_member",
                    "Every visibility entry must be an active group member",
                )
    bet, outcomes = await repository.create_bet(
        session,
        group_id=group_id,
        created_by=creator_id,
        question=payload.question,
        description=payload.description,
        visibility=BetVisibility.GROUP,
        end_time=aware(payload.end_time),
        outcome_labels=payload.outcome_labels,
        liquidity_seed=Decimal(settings.default_liquidity_seed),
        visible_to_user_ids=payload.visible_to_user_ids,
    )
    return await build_response(session, bet, outcomes)


async def create_public_bet(
    session: AsyncSession,
    *,
    creator_id: UUID,
    payload: CreateBetRequest,
    settings: Settings,
) -> BetResponse:
    if payload.visible_to_user_ids is not None:
        raise DomainError(
            "public_visibility_forbidden",
            "Standalone public bets cannot have a group visibility allow-list",
        )
    if aware(payload.end_time) <= utc_now():
        raise DomainError("invalid_end_time", "Bet end time must be in the future")
    bet, outcomes = await repository.create_bet(
        session,
        group_id=None,
        created_by=creator_id,
        question=payload.question,
        description=payload.description,
        visibility=BetVisibility.PUBLIC,
        end_time=aware(payload.end_time),
        outcome_labels=payload.outcome_labels,
        liquidity_seed=Decimal(settings.default_liquidity_seed),
        visible_to_user_ids=None,
    )
    return await build_response(session, bet, outcomes)


async def list_visible_group_bets(
    session: AsyncSession, *, group_id: UUID, user_id: UUID
) -> list[BetResponse]:
    membership = await get_membership_state(session, group_id, user_id)
    if membership is None:
        raise DomainError("not_group_member", "You are not a member of this group", 403)
    results: list[BetResponse] = []
    for bet in await repository.list_group_bets(session, group_id):
        if membership.status is MembershipStatus.REMOVED:
            from app.modules.trading.service import has_position

            if await has_position(session, bet_id=bet.id, user_id=user_id):
                results.append(await build_response(session, bet))
            continue
        if await _visibility_allows(
            session,
            bet=bet,
            user_id=user_id,
            member_role=membership.role,
        ):
            results.append(await build_response(session, bet))
    return results


async def list_public_bets(session: AsyncSession) -> list[BetResponse]:
    return [
        await build_response(session, bet)
        for bet in await repository.list_public_bets(session)
    ]


async def get_visible_bet(
    session: AsyncSession, *, bet_id: UUID, user_id: UUID
) -> BetResponse:
    bet = await repository.get_bet(session, bet_id)
    if bet is None or bet.status is BetStatus.CANCELLED:
        raise DomainError("bet_not_found", "Bet not found", 404)
    if bet.visibility is BetVisibility.PUBLIC:
        return await build_response(session, bet)
    if bet.group_id is None:
        raise DomainError("invalid_market", "Group bet has no group", 500)
    membership = await get_membership_state(session, bet.group_id, user_id)
    if membership is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    if membership.status is MembershipStatus.ACTIVE and await _visibility_allows(
        session,
        bet=bet,
        user_id=user_id,
        member_role=membership.role,
    ):
        return await build_response(session, bet)
    if membership.status is MembershipStatus.REMOVED:
        from app.modules.trading.service import has_position

        if await has_position(session, bet_id=bet.id, user_id=user_id):
            return await build_response(session, bet)
    raise DomainError("bet_not_found", "Bet not found", 404)


async def edit_end_time(
    session: AsyncSession,
    *,
    bet_id: UUID,
    editor_id: UUID,
    new_end_time: datetime,
) -> BetResponse:
    bet = await repository.get_bet(session, bet_id, lock=True)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    if bet.status in {BetStatus.RESOLVED, BetStatus.CANCELLED}:
        raise DomainError("bet_immutable", "Resolved or cancelled bets cannot be edited", 409)
    if bet.visibility is BetVisibility.GROUP:
        if bet.group_id is None:
            raise DomainError("invalid_market", "Group bet has no group", 500)
        await require_admin(session, bet.group_id, editor_id)
    elif bet.created_by != editor_id:
        raise DomainError(
            "creator_required",
            "Only the public bet creator can edit its end time",
            403,
        )
    replacement = aware(new_end_time)
    if replacement <= utc_now():
        raise DomainError("invalid_end_time", "The replacement end time must be in the future")
    old_end_time = aware(bet.end_time)
    bet.end_time = replacement
    bet.status = BetStatus.OPEN
    await repository.add_edit_event(
        session,
        bet_id=bet.id,
        edited_by=editor_id,
        old_end_time=old_end_time,
        new_end_time=replacement,
    )
    await session.flush()
    return await build_response(session, bet)


async def cancel_bet(
    session: AsyncSession,
    *,
    bet_id: UUID,
    actor_id: UUID,
) -> CancellationResponse:
    bet = await repository.get_bet(session, bet_id, lock=True)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    if bet.status is BetStatus.RESOLVED:
        raise DomainError(
            "resolved_bet_cannot_be_cancelled",
            "Resolved bets cannot be cancelled",
            409,
        )
    if bet.status is BetStatus.CANCELLED:
        raise DomainError("bet_already_cancelled", "This bet is already cancelled", 409)

    if bet.visibility is BetVisibility.GROUP:
        if bet.group_id is None:
            raise DomainError("invalid_market", "Group bet has no group", 500)
        membership = await require_membership(session, bet.group_id, actor_id)
        if bet.created_by != actor_id and membership.role is not MemberRole.ADMIN:
            raise DomainError(
                "cancel_not_allowed",
                "Only the bet creator or a group admin can cancel this bet",
                403,
            )
    elif bet.created_by != actor_id:
        raise DomainError(
            "creator_required",
            "Only the public bet creator can cancel it",
            403,
        )

    total_refund = Decimal(0)
    stakes = await get_bet_stakes(session, bet.id)
    for user_id, refund in stakes:
        await add_entry(
            session,
            user_id=user_id,
            amount=refund,
            entry_type=LedgerEntryType.BET_REFUND,
            bet_id=bet.id,
        )
        total_refund += refund
    cancelled_at = utc_now()
    bet.status = BetStatus.CANCELLED
    bet.cancelled_at = cancelled_at
    await session.flush()
    business_event(
        logger,
        "bet_cancelled",
        bet_id=str(bet.id),
        actor_id=str(actor_id),
        refunded_users=len(stakes),
        refunded_points=str(total_refund),
    )
    return CancellationResponse(
        bet_id=bet.id,
        refunded_users=len(stakes),
        refunded_points=total_refund,
        cancelled_at=cancelled_at,
    )


async def list_resolved_bet_ids(
    session: AsyncSession,
    *,
    group_id: UUID | None,
    public: bool,
    resolved_since: datetime | None,
) -> list[UUID]:
    return await repository.list_resolved_bet_ids(
        session,
        group_id=group_id,
        public=public,
        resolved_since=resolved_since,
    )


async def list_unsettled_group_bet_ids(
    session: AsyncSession, group_id: UUID
) -> list[UUID]:
    return await repository.list_unsettled_group_bet_ids(session, group_id)

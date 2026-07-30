import logging
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.logging import business_event
from app.modules.amm import Side, buy_shares, get_prices
from app.modules.bets import repository as bets_repository
from app.modules.bets.models import BetStatus, Outcome
from app.modules.bets.service import get_visible_bet, refresh_time_status
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry, get_balance
from app.modules.trading import repository
from app.modules.trading.models import Position
from app.modules.trading.schemas import BuyPreviewResponse, TradeResponse
from app.modules.users.service import lock_user

logger = logging.getLogger(__name__)
SCALE = Decimal("0.00000001")


def money(value: Decimal) -> Decimal:
    return value.quantize(SCALE, rounding=ROUND_HALF_UP)


async def has_position(session: AsyncSession, *, bet_id: UUID, user_id: UUID) -> bool:
    return await repository.has_position(session, bet_id=bet_id, user_id=user_id)


async def list_user_positions(
    session: AsyncSession, *, bet_id: UUID, user_id: UUID
) -> list[Position]:
    return await repository.list_user_positions(
        session,
        bet_id=bet_id,
        user_id=user_id,
    )


async def list_outcome_positions(
    session: AsyncSession, *, bet_id: UUID, outcome_id: UUID
) -> list[Position]:
    return await repository.list_outcome_positions(
        session,
        bet_id=bet_id,
        outcome_id=outcome_id,
    )


async def has_unsettled_group_position(
    session: AsyncSession, *, group_id: UUID, user_id: UUID
) -> bool:
    from app.modules.bets.service import list_unsettled_group_bet_ids

    bet_ids = await list_unsettled_group_bet_ids(session, group_id)
    return await repository.has_position_in_bets(
        session,
        user_id=user_id,
        bet_ids=bet_ids,
    )


def _quote(
    *,
    outcome_id: UUID,
    amount: Decimal,
    outcomes: list[Outcome],
) -> BuyPreviewResponse:
    if len(outcomes) != 2:
        raise DomainError("invalid_market", "A v1 market must have exactly two outcomes", 500)
    selected = next(
        (outcome for outcome in outcomes if outcome.id == outcome_id),
        None,
    )
    if selected is None:
        raise DomainError("outcome_not_found", "Outcome does not belong to this bet", 404)
    side = Side.YES if selected.display_order == 0 else Side.NO
    result = buy_shares(
        outcomes[0].pool_shares,
        outcomes[1].pool_shares,
        amount,
        side,
    )
    prices = get_prices(result.pool_yes, result.pool_no)
    return BuyPreviewResponse(
        outcome_id=outcome_id,
        amount=money(amount),
        shares_out=money(result.shares_out),
        price_yes_after=prices.yes,
        price_no_after=prices.no,
    )


async def preview_buy(
    session: AsyncSession,
    *,
    bet_id: UUID,
    user_id: UUID,
    outcome_id: UUID,
    amount: Decimal,
    settings: Settings,
) -> BuyPreviewResponse:
    await get_visible_bet(session, bet_id=bet_id, user_id=user_id)
    if amount < settings.minimum_trade_amount:
        raise DomainError(
            "trade_below_minimum",
            f"The minimum trade is {settings.minimum_trade_amount} point",
        )
    bet = await bets_repository.get_bet(session, bet_id)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    refresh_time_status(bet)
    if bet.status is not BetStatus.OPEN:
        raise DomainError("bet_not_open", "This bet is no longer open for trading", 409)
    outcomes = await bets_repository.get_outcomes(session, bet_id)
    return _quote(outcome_id=outcome_id, amount=amount, outcomes=list(outcomes))


async def place_buy(
    session: AsyncSession,
    *,
    bet_id: UUID,
    user_id: UUID,
    outcome_id: UUID,
    amount: Decimal,
    settings: Settings,
) -> TradeResponse:
    stake = money(amount)
    if stake < settings.minimum_trade_amount:
        raise DomainError(
            "trade_below_minimum",
            f"The minimum trade is {settings.minimum_trade_amount} point",
        )
    await lock_user(session, user_id)
    await get_visible_bet(session, bet_id=bet_id, user_id=user_id)
    bet = await bets_repository.get_bet(session, bet_id, lock=True)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    refresh_time_status(bet)
    if bet.status is not BetStatus.OPEN:
        raise DomainError("bet_not_open", "This bet is no longer open for trading", 409)
    balance = await get_balance(session, user_id)
    if balance < stake:
        raise DomainError(
            "insufficient_balance",
            "Your points balance is too low for this trade",
            409,
        )

    outcomes = await bets_repository.get_outcomes(session, bet_id, lock=True)
    quote = _quote(outcome_id=outcome_id, amount=stake, outcomes=list(outcomes))
    selected = next(outcome for outcome in outcomes if outcome.id == outcome_id)
    side = Side.YES if selected.display_order == 0 else Side.NO
    result = buy_shares(outcomes[0].pool_shares, outcomes[1].pool_shares, stake, side)
    outcomes[0].pool_shares = money(result.pool_yes)
    outcomes[1].pool_shares = money(result.pool_no)

    position = await repository.get_position(
        session,
        user_id=user_id,
        bet_id=bet_id,
        outcome_id=outcome_id,
        lock=True,
    )
    shares = money(result.shares_out)
    if position is None:
        position = Position(
            user_id=user_id,
            bet_id=bet_id,
            outcome_id=outcome_id,
            shares=shares,
            points_spent=stake,
        )
        session.add(position)
    else:
        position.shares = money(position.shares + shares)
        position.points_spent = money(position.points_spent + stake)

    await add_entry(
        session,
        user_id=user_id,
        amount=-stake,
        entry_type=LedgerEntryType.BET_PLACED,
        bet_id=bet_id,
    )
    await session.flush()
    remaining_balance = money(balance - stake)
    business_event(
        logger,
        "bet_placed",
        user_id=str(user_id),
        bet_id=str(bet_id),
        outcome_id=str(outcome_id),
        amount=str(stake),
        shares_out=str(shares),
        pool_after={
            "yes": str(outcomes[0].pool_shares),
            "no": str(outcomes[1].pool_shares),
        },
    )
    return TradeResponse(
        outcome_id=quote.outcome_id,
        amount=quote.amount,
        shares_out=shares,
        price_yes_after=quote.price_yes_after,
        price_no_after=quote.price_no_after,
        remaining_balance=remaining_balance,
        position_shares=position.shares,
    )

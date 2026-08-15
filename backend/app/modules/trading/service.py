import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.locks import local_market_lock
from app.core.logging import business_event
from app.core.money import money
from app.modules.amm import Side, buy_shares, get_prices, quote_trade
from app.modules.amm import prices as lmsr_prices
from app.modules.bets import repository as bets_repository
from app.modules.bets.models import Bet, BetStatus, Outcome, PricingMethod
from app.modules.bets.service import get_visible_bet, refresh_time_status
from app.modules.house.models import HouseLedgerEntryType
from app.modules.house.service import add_house_entry
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry, get_balance
from app.modules.trading import repository
from app.modules.trading.models import Position, Trade, TradeSide
from app.modules.trading.schemas import (
    BuyPreviewResponse,
    LmsrPriceResponse,
    LmsrQuoteResponse,
    LmsrTradeResponse,
    TradeResponse,
)
from app.modules.users.service import lock_user

logger = logging.getLogger(__name__)
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
    if bet.pricing_method is not PricingMethod.CPMM:
        raise DomainError(
            "pricing_method_mismatch",
            "Use the LMSR quote endpoint for this market",
            409,
        )
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
    if bet.pricing_method is not PricingMethod.CPMM:
        raise DomainError(
            "pricing_method_mismatch",
            "Use the LMSR trade endpoint for this market",
            409,
        )
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


def _lmsr_state(bet: Bet) -> tuple[Decimal, Decimal, Decimal]:
    if bet.pricing_method is not PricingMethod.LMSR:
        raise DomainError(
            "pricing_method_mismatch",
            "This endpoint is available only for LMSR markets",
            409,
        )
    if bet.q_yes is None or bet.q_no is None or bet.b_liquidity is None:
        raise DomainError("invalid_market", "LMSR state is incomplete", 500)
    return bet.q_yes, bet.q_no, bet.b_liquidity


async def get_lmsr_price(session: AsyncSession, *, bet_id: UUID) -> LmsrPriceResponse:
    bet = await bets_repository.get_bet(session, bet_id)
    if bet is None or bet.status is BetStatus.CANCELLED:
        raise DomainError("bet_not_found", "Bet not found", 404)
    q_yes, q_no, liquidity = _lmsr_state(bet)
    current = lmsr_prices(q_yes, q_no, liquidity)
    return LmsrPriceResponse(
        bet_id=bet.id,
        price_yes=money(current.yes),
        price_no=money(current.no),
        q_yes=q_yes,
        q_no=q_no,
        b_liquidity=liquidity,
    )


async def quote_lmsr_trade(
    session: AsyncSession,
    *,
    bet_id: UUID,
    side: TradeSide,
    shares: Decimal,
) -> LmsrQuoteResponse:
    bet = await bets_repository.get_bet(session, bet_id)
    if bet is None or bet.status is BetStatus.CANCELLED:
        raise DomainError("bet_not_found", "Bet not found", 404)
    refresh_time_status(bet)
    if bet.status is not BetStatus.OPEN:
        raise DomainError("bet_not_open", "This bet is no longer open for trading", 409)
    q_yes, q_no, liquidity = _lmsr_state(bet)
    delta = money(shares)
    if delta == 0:
        raise DomainError("trade_too_small", "Shares are below the supported precision")
    try:
        result = quote_trade(q_yes, q_no, liquidity, Side(side.value), delta)
    except ValueError as exc:
        raise DomainError("invalid_trade", str(exc)) from exc
    signed_cost = money(result.cost)
    if signed_cost == 0:
        raise DomainError("trade_too_small", "Trade cost is below the supported precision")
    average_price = money(abs(signed_cost / delta))
    return LmsrQuoteResponse(
        bet_id=bet.id,
        side=side,
        delta_shares=delta,
        cost=signed_cost,
        average_price=average_price,
        q_yes=q_yes,
        q_no=q_no,
        b_liquidity=liquidity,
        q_yes_after=money(result.q_yes_after),
        q_no_after=money(result.q_no_after),
        price_yes=money(lmsr_prices(q_yes, q_no, liquidity).yes),
        price_no=money(lmsr_prices(q_yes, q_no, liquidity).no),
        price_yes_after=money(result.prices_after.yes),
        price_no_after=money(result.prices_after.no),
    )


async def execute_lmsr_trade(
    session: AsyncSession,
    *,
    bet_id: UUID,
    user_id: UUID,
    side: TradeSide,
    shares: Decimal,
) -> LmsrTradeResponse:
    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        async with local_market_lock(bet_id):
            result = await _execute_lmsr_trade_locked(
                session,
                bet_id=bet_id,
                user_id=user_id,
                side=side,
                shares=shares,
            )
            # The request dependency normally commits after the endpoint returns,
            # which would release this local lock too early. Commit before releasing
            # the SQLite fallback lock so the next request observes the new state.
            await session.commit()
            return result
    return await _execute_lmsr_trade_locked(
        session,
        bet_id=bet_id,
        user_id=user_id,
        side=side,
        shares=shares,
    )


async def _execute_lmsr_trade_locked(
    session: AsyncSession,
    *,
    bet_id: UUID,
    user_id: UUID,
    side: TradeSide,
    shares: Decimal,
) -> LmsrTradeResponse:
    await lock_user(session, user_id)
    await get_visible_bet(session, bet_id=bet_id, user_id=user_id)
    bet = await bets_repository.get_bet(session, bet_id, lock=True)
    if bet is None:
        raise DomainError("bet_not_found", "Bet not found", 404)
    refresh_time_status(bet)
    if bet.status is not BetStatus.OPEN:
        raise DomainError("bet_not_open", "This bet is no longer open for trading", 409)
    q_yes, q_no, _liquidity = _lmsr_state(bet)

    outcomes = await bets_repository.get_outcomes(session, bet.id, lock=True)
    if len(outcomes) != 2:
        raise DomainError("invalid_market", "A binary LMSR market needs two outcomes", 500)
    outcome = outcomes[0] if side is TradeSide.YES else outcomes[1]
    position = await repository.get_position(
        session,
        user_id=user_id,
        bet_id=bet.id,
        outcome_id=outcome.id,
        lock=True,
    )
    delta = money(shares)
    if delta < 0 and (position is None or position.shares < -delta):
        raise DomainError(
            "insufficient_shares",
            "You cannot sell more shares than you currently hold",
            409,
        )

    quote = await quote_lmsr_trade(
        session,
        bet_id=bet.id,
        side=side,
        shares=delta,
    )
    balance = await get_balance(session, user_id)
    if quote.cost > 0 and balance < quote.cost:
        raise DomainError(
            "insufficient_balance",
            "Your points balance is too low for this trade",
            409,
        )

    bet.q_yes = quote.q_yes_after
    bet.q_no = quote.q_no_after
    bet.house_cash_balance = money(bet.house_cash_balance + quote.cost)
    outcomes[0].pool_shares = bet.q_yes
    outcomes[1].pool_shares = bet.q_no

    if position is None:
        position = Position(
            user_id=user_id,
            bet_id=bet.id,
            outcome_id=outcome.id,
            shares=delta,
            points_spent=quote.cost,
        )
        session.add(position)
    else:
        position.shares = money(position.shares + delta)
        position.points_spent = money(position.points_spent + quote.cost)
        if position.shares == 0:
            position.points_spent = Decimal(0)

    trade = await repository.add_trade(
        session,
        Trade(
            bet_id=bet.id,
            user_id=user_id,
            outcome_id=outcome.id,
            sequence=await repository.next_trade_sequence(session, bet.id),
            side=side,
            delta_shares=delta,
            cost=quote.cost,
            house_cash_flow=quote.cost,
            q_yes_after=bet.q_yes,
            q_no_after=bet.q_no,
        ),
    )
    await add_entry(
        session,
        user_id=user_id,
        amount=-quote.cost,
        entry_type=LedgerEntryType.MARKET_TRADE,
        bet_id=bet.id,
    )
    await add_house_entry(
        session,
        bet_id=bet.id,
        group_id=bet.group_id,
        trade_id=trade.id,
        entry_type=HouseLedgerEntryType.TRADE,
        cash_delta=quote.cost,
    )
    await session.flush()
    remaining_balance = money(balance - quote.cost)
    business_event(
        logger,
        "lmsr_trade_executed",
        trade_id=str(trade.id),
        user_id=str(user_id),
        bet_id=str(bet.id),
        side=side.value,
        delta_shares=str(delta),
        cost=str(quote.cost),
        house_cash_balance=str(bet.house_cash_balance),
    )
    return LmsrTradeResponse(
        **quote.model_dump(),
        trade_id=trade.id,
        outcome_id=outcome.id,
        remaining_balance=remaining_balance,
        position_shares=position.shares,
        house_cash_flow=quote.cost,
    )

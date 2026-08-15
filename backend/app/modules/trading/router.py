from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, SessionDependency, SettingsDependency
from app.modules.bets.service import get_visible_bet
from app.modules.trading import repository
from app.modules.trading.models import TradeSide
from app.modules.trading.schemas import (
    BuyPreviewResponse,
    BuyRequest,
    LmsrPriceResponse,
    LmsrQuoteResponse,
    LmsrTradeRequest,
    LmsrTradeResponse,
    PositionResponse,
    TradeAuditResponse,
    TradeResponse,
)
from app.modules.trading.service import (
    execute_lmsr_trade,
    get_lmsr_price,
    list_user_positions,
    place_buy,
    preview_buy,
    quote_lmsr_trade,
)

router = APIRouter(tags=["trading"])


@router.post("/bets/{bet_id}/preview-buy", response_model=BuyPreviewResponse)
async def preview_buy_route(
    bet_id: UUID,
    payload: BuyRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> BuyPreviewResponse:
    return await preview_buy(
        session,
        bet_id=bet_id,
        user_id=current_user.id,
        outcome_id=payload.outcome_id,
        amount=payload.amount,
        settings=settings,
    )


@router.post("/bets/{bet_id}/buy", response_model=TradeResponse)
async def place_buy_route(
    bet_id: UUID,
    payload: BuyRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> TradeResponse:
    return await place_buy(
        session,
        bet_id=bet_id,
        user_id=current_user.id,
        outcome_id=payload.outcome_id,
        amount=payload.amount,
        settings=settings,
    )


@router.get("/bets/{bet_id}/positions/me", response_model=list[PositionResponse])
async def list_my_positions_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[PositionResponse]:
    await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)
    return [
        PositionResponse.model_validate(position)
        for position in await list_user_positions(
            session,
            bet_id=bet_id,
            user_id=current_user.id,
        )
    ]


@router.get("/markets/{bet_id}/price", response_model=LmsrPriceResponse)
async def lmsr_price_route(
    bet_id: UUID,
    session: SessionDependency,
) -> LmsrPriceResponse:
    return await get_lmsr_price(session, bet_id=bet_id)


@router.get("/markets/{bet_id}/quote", response_model=LmsrQuoteResponse)
async def lmsr_quote_route(
    bet_id: UUID,
    session: SessionDependency,
    side: TradeSide,
    shares: Annotated[Decimal, Query(max_digits=20, decimal_places=8)],
) -> LmsrQuoteResponse:
    return await quote_lmsr_trade(
        session,
        bet_id=bet_id,
        side=side,
        shares=shares,
    )


@router.post("/markets/{bet_id}/trade", response_model=LmsrTradeResponse)
async def lmsr_trade_route(
    bet_id: UUID,
    payload: LmsrTradeRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> LmsrTradeResponse:
    return await execute_lmsr_trade(
        session,
        bet_id=bet_id,
        user_id=current_user.id,
        side=payload.side,
        shares=payload.shares,
    )


@router.get("/markets/{bet_id}/trades", response_model=list[TradeAuditResponse])
async def lmsr_trades_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[TradeAuditResponse]:
    await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)
    return [
        TradeAuditResponse.model_validate(trade)
        for trade in await repository.list_trades(session, bet_id)
    ]

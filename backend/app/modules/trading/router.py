from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDependency, SettingsDependency
from app.modules.bets.service import get_visible_bet
from app.modules.trading.schemas import (
    BuyPreviewResponse,
    BuyRequest,
    PositionResponse,
    TradeResponse,
)
from app.modules.trading.service import (
    list_user_positions,
    place_buy,
    preview_buy,
)

router = APIRouter(prefix="/bets", tags=["trading"])


@router.post("/{bet_id}/preview-buy", response_model=BuyPreviewResponse)
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


@router.post("/{bet_id}/buy", response_model=TradeResponse)
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


@router.get("/{bet_id}/positions/me", response_model=list[PositionResponse])
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


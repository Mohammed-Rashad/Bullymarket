from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDependency, SettingsDependency
from app.modules.resolution.schemas import (
    ResolutionEventResponse,
    ResolutionResponse,
    ResolveRequest,
)
from app.modules.resolution.service import list_resolution_events, resolve_bet

router = APIRouter(prefix="/bets", tags=["resolution"])


@router.post("/{bet_id}/resolve", response_model=ResolutionResponse)
async def resolve_bet_route(
    bet_id: UUID,
    payload: ResolveRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> ResolutionResponse:
    return await resolve_bet(
        session,
        bet_id=bet_id,
        outcome_id=payload.outcome_id,
        resolver_id=current_user.id,
        settings=settings,
    )


@router.get(
    "/{bet_id}/resolution-events",
    response_model=list[ResolutionEventResponse],
)
async def resolution_events_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[ResolutionEventResponse]:
    return [
        ResolutionEventResponse.model_validate(event)
        for event in await list_resolution_events(
            session,
            bet_id=bet_id,
            user_id=current_user.id,
        )
    ]

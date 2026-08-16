from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, SessionDependency, SettingsDependency
from app.modules.bets import repository
from app.modules.bets.models import BetStatus
from app.modules.bets.schemas import (
    BetEditEventResponse,
    BetResponse,
    CancellationResponse,
    CreateBetRequest,
    EditEndTimeRequest,
    PaginatedBetsResponse,
)
from app.modules.bets.service import (
    cancel_bet,
    create_group_bet,
    create_public_bet,
    edit_end_time,
    get_visible_bet,
    list_public_bets,
    list_visible_group_bets,
)

router = APIRouter(tags=["bets"])

StatusFilter = Annotated[BetStatus | None, Query(alias="status")]
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.post(
    "/groups/{group_id}/bets",
    response_model=BetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group_bet_route(
    group_id: UUID,
    payload: CreateBetRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> BetResponse:
    return await create_group_bet(
        session,
        group_id=group_id,
        creator_id=current_user.id,
        payload=payload,
        settings=settings,
    )


@router.get("/groups/{group_id}/bets", response_model=PaginatedBetsResponse)
async def list_group_bets_route(
    group_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
    status_filter: StatusFilter = None,
    page: PageNumber = 1,
    page_size: PageSize = 12,
) -> PaginatedBetsResponse:
    return await list_visible_group_bets(
        session,
        group_id=group_id,
        user_id=current_user.id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/public-bets",
    response_model=BetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_bet_route(
    payload: CreateBetRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> BetResponse:
    return await create_public_bet(
        session,
        creator_id=current_user.id,
        payload=payload,
        settings=settings,
    )


@router.get("/public-bets", response_model=PaginatedBetsResponse)
async def list_public_bets_route(
    _current_user: CurrentUser,
    session: SessionDependency,
    status_filter: StatusFilter = None,
    page: PageNumber = 1,
    page_size: PageSize = 12,
) -> PaginatedBetsResponse:
    return await list_public_bets(
        session,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/bets/{bet_id}", response_model=BetResponse)
async def get_bet_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> BetResponse:
    return await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)


@router.patch("/bets/{bet_id}/end-time", response_model=BetResponse)
async def edit_end_time_route(
    bet_id: UUID,
    payload: EditEndTimeRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> BetResponse:
    return await edit_end_time(
        session,
        bet_id=bet_id,
        editor_id=current_user.id,
        new_end_time=payload.end_time,
    )


@router.get(
    "/bets/{bet_id}/edit-events",
    response_model=list[BetEditEventResponse],
)
async def list_edit_events_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[BetEditEventResponse]:
    await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)
    return [
        BetEditEventResponse.model_validate(event)
        for event in await repository.list_edit_events(session, bet_id)
    ]


@router.delete("/bets/{bet_id}", response_model=CancellationResponse)
async def cancel_bet_route(
    bet_id: UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUser,
) -> CancellationResponse:
    return await cancel_bet(
        session,
        bet_id=bet_id,
        actor_id=current_user.id,
        settings=settings,
    )

from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDependency
from app.modules.bets.service import get_visible_bet
from app.modules.groups.service import require_admin
from app.modules.house import repository
from app.modules.house.schemas import HouseLedgerEntryResponse, HouseSummaryResponse
from app.modules.house.service import get_summary

router = APIRouter(tags=["house"])


@router.get("/house", response_model=HouseSummaryResponse)
async def global_house_summary_route(
    session: SessionDependency,
    _current_user: CurrentUser,
) -> HouseSummaryResponse:
    return await get_summary(session)


@router.get("/groups/{group_id}/house", response_model=HouseSummaryResponse)
async def group_house_summary_route(
    group_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> HouseSummaryResponse:
    await require_admin(session, group_id, current_user.id)
    return await get_summary(session, group_id=group_id)


@router.get("/bets/{bet_id}/house", response_model=HouseSummaryResponse)
async def bet_house_summary_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> HouseSummaryResponse:
    await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)
    return await get_summary(session, bet_id=bet_id)


@router.get(
    "/bets/{bet_id}/house-ledger",
    response_model=list[HouseLedgerEntryResponse],
)
async def bet_house_ledger_route(
    bet_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> list[HouseLedgerEntryResponse]:
    await get_visible_bet(session, bet_id=bet_id, user_id=current_user.id)
    return [
        HouseLedgerEntryResponse.model_validate(entry)
        for entry in await repository.list_entries(session, bet_id)
    ]

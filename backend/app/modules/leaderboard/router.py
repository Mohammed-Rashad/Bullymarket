from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDependency
from app.modules.leaderboard.schemas import LeaderboardResponse, LeaderboardWindow
from app.modules.leaderboard.service import (
    get_group_leaderboard,
    get_public_leaderboard,
)

router = APIRouter(tags=["leaderboard"])


@router.get(
    "/groups/{group_id}/leaderboard",
    response_model=LeaderboardResponse,
)
async def group_leaderboard_route(
    group_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
    window: LeaderboardWindow = LeaderboardWindow.WEEKLY,
) -> LeaderboardResponse:
    return await get_group_leaderboard(
        session,
        group_id=group_id,
        requesting_user_id=current_user.id,
        window=window,
    )


@router.get("/leaderboards/public", response_model=LeaderboardResponse)
async def public_leaderboard_route(
    _current_user: CurrentUser,
    session: SessionDependency,
    window: LeaderboardWindow = LeaderboardWindow.WEEKLY,
) -> LeaderboardResponse:
    return await get_public_leaderboard(session, window=window)


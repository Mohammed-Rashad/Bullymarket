from fastapi import APIRouter

from app.api.dependencies import CurrentUser, SessionDependency
from app.modules.users.schemas import UserProfile
from app.modules.users.service import get_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfile)
async def read_current_user(session: SessionDependency, current_user: CurrentUser) -> UserProfile:
    user, balance = await get_profile(session, current_user)
    return UserProfile(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        balance=balance,
    )


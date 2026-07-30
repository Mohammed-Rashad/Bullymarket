from fastapi import APIRouter, status

from app.api.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.schemas import LoginRequest, SignupRequest, TokenResponse
from app.modules.auth.service import login, signup

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup_route(
    payload: SignupRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return TokenResponse(access_token=await signup(session, payload, settings))


@router.post("/login", response_model=TokenResponse)
async def login_route(
    payload: LoginRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return TokenResponse(access_token=await login(session, payload, settings))


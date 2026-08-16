from fastapi import APIRouter, status

from app.api.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    VerificationChallengeResponse,
    VerifySignupRequest,
)
from app.modules.auth.service import (
    login,
    request_password_reset,
    request_signup,
    reset_password,
    verify_signup,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=VerificationChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def signup_route(
    payload: SignupRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> VerificationChallengeResponse:
    return await request_signup(session, payload, settings)


@router.post("/signup/verify", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def verify_signup_route(
    payload: VerifySignupRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return TokenResponse(access_token=await verify_signup(session, payload, settings))


@router.post(
    "/forgot-password",
    response_model=VerificationChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password_route(
    payload: ForgotPasswordRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> VerificationChallengeResponse:
    return await request_password_reset(session, payload, settings)


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password_route(
    payload: ResetPasswordRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return TokenResponse(access_token=await reset_password(session, payload, settings))


@router.post("/login", response_model=TokenResponse)
async def login_route(
    payload: LoginRequest,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    return TokenResponse(access_token=await login(session, payload, settings))

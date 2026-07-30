from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.exceptions import DomainError
from app.core.security import decode_access_token
from app.modules.users.models import User
from app.modules.users.repository import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: SessionDependency,
    settings: SettingsDependency,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    user_id = decode_access_token(token, settings)
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise DomainError("invalid_token", "The account for this token no longer exists", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


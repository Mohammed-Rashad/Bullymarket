from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.schemas import LoginRequest, SignupRequest
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry
from app.modules.users.repository import create_user, get_user_by_email


async def signup(session: AsyncSession, payload: SignupRequest, settings: Settings) -> str:
    if await get_user_by_email(session, str(payload.email)) is not None:
        raise DomainError("email_taken", "An account with this email already exists", 409)
    try:
        user = await create_user(
            session,
            email=str(payload.email),
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
        )
        user.last_refill_at = datetime.now(UTC)
        await add_entry(
            session,
            user_id=user.id,
            amount=Decimal(settings.default_starting_balance),
            entry_type=LedgerEntryType.REFILL,
        )
    except IntegrityError as exc:
        raise DomainError("email_taken", "An account with this email already exists", 409) from exc
    return create_access_token(user.id, settings)


async def login(session: AsyncSession, payload: LoginRequest, settings: Settings) -> str:
    user = await get_user_by_email(session, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise DomainError("invalid_credentials", "Email or password is incorrect", 401)
    return create_access_token(user.id, settings)

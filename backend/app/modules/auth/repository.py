from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import VerificationChallenge, VerificationPurpose


async def latest_challenge(
    session: AsyncSession,
    *,
    email: str,
    purpose: VerificationPurpose,
    lock: bool = False,
) -> VerificationChallenge | None:
    statement = (
        select(VerificationChallenge)
        .where(
            VerificationChallenge.email == email.lower(),
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed_at.is_(None),
        )
        .order_by(VerificationChallenge.created_at.desc())
        .limit(1)
    )
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def consume_active_challenges(
    session: AsyncSession,
    *,
    email: str,
    purpose: VerificationPurpose,
    consumed_at: datetime,
) -> None:
    await session.execute(
        update(VerificationChallenge)
        .where(
            VerificationChallenge.email == email.lower(),
            VerificationChallenge.purpose == purpose,
            VerificationChallenge.consumed_at.is_(None),
        )
        .values(consumed_at=consumed_at)
    )

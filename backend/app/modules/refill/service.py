import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import business_event
from app.modules.ledger.models import LedgerEntryType
from app.modules.ledger.service import add_entry
from app.modules.users.service import list_due_for_refill

logger = logging.getLogger(__name__)


async def run_refills(
    session: AsyncSession,
    *,
    settings: Settings,
    now: datetime | None = None,
) -> int:
    run_at = now or datetime.now(UTC)
    cutoff = run_at - timedelta(days=settings.refill_interval_days)
    due_users = await list_due_for_refill(session, cutoff)
    for user in due_users:
        await add_entry(
            session,
            user_id=user.id,
            amount=Decimal(settings.refill_amount),
            entry_type=LedgerEntryType.REFILL,
        )
        user.last_refill_at = run_at
    await session.flush()
    business_event(
        logger,
        "refill_completed",
        eligible_users=len(due_users),
        refill_amount=settings.refill_amount,
    )
    return len(due_users)


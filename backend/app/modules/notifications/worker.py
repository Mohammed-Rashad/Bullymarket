import asyncio
import logging
from datetime import UTC, datetime

from app.core import db
from app.core.config import Settings, get_settings
from app.modules.bets import repository as bets_repository
from app.modules.bets.models import BetStatus
from app.modules.notifications.email import deliver_pending_emails
from app.modules.notifications.models import NotificationKind
from app.modules.notifications.service import notify_group_bet

logger = logging.getLogger(__name__)


async def run_notification_cycle(settings: Settings) -> tuple[int, int]:
    notifications = 0
    async with db.SessionFactory.begin() as session:
        for bet in await bets_repository.list_due_group_bets(session, datetime.now(UTC)):
            bet.status = BetStatus.CLOSED
            notifications += await notify_group_bet(
                session,
                bet=bet,
                kind=NotificationKind.BET_CLOSED,
                settings=settings,
            )
    async with db.SessionFactory.begin() as session:
        emails = await deliver_pending_emails(session, settings)
    return notifications, emails


async def main() -> None:
    settings = get_settings()
    while True:
        try:
            await run_notification_cycle(settings)
        except Exception:
            logger.exception("Notification worker cycle failed")
        await asyncio.sleep(settings.notification_worker_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())

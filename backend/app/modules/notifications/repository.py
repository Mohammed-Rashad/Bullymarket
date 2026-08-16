from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import (
    EmailOutbox,
    EmailOutboxStatus,
    Notification,
    NotificationKind,
    NotificationPreference,
)


async def get_notification(
    session: AsyncSession, notification_id: UUID, user_id: UUID
) -> Notification | None:
    return await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )


async def find_notification(
    session: AsyncSession, *, user_id: UUID, kind: NotificationKind, bet_id: UUID
) -> Notification | None:
    return await session.scalar(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.kind == kind,
            Notification.bet_id == bet_id,
        )
    )


async def list_notifications(
    session: AsyncSession,
    *,
    user_id: UUID,
    unread_only: bool,
    page: int,
    page_size: int,
) -> tuple[list[Notification], int, int]:
    predicates = [Notification.user_id == user_id]
    if unread_only:
        predicates.append(Notification.read_at.is_(None))
    total = int(
        await session.scalar(
            select(func.count()).select_from(Notification).where(*predicates)
        )
        or 0
    )
    unread = int(
        await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        or 0
    )
    rows = list(
        await session.scalars(
            select(Notification)
            .where(*predicates)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total, unread


async def mark_all_read(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def get_preferences(
    session: AsyncSession, user_id: UUID
) -> NotificationPreference | None:
    return await session.get(NotificationPreference, user_id)


async def pending_emails(
    session: AsyncSession, *, now: datetime, limit: int
) -> list[EmailOutbox]:
    return list(
        await session.scalars(
            select(EmailOutbox)
            .where(
                EmailOutbox.status == EmailOutboxStatus.PENDING,
                EmailOutbox.available_at <= now,
            )
            .order_by(EmailOutbox.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )

from datetime import UTC, datetime
from html import escape
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.modules.bets import repository as bets_repository
from app.modules.bets.models import Bet, BetVisibility
from app.modules.groups import repository as groups_repository
from app.modules.groups.models import MemberRole, MembershipStatus
from app.modules.notifications import repository
from app.modules.notifications.models import (
    EmailOutbox,
    Notification,
    NotificationKind,
    NotificationPreference,
)
from app.modules.notifications.schemas import (
    NotificationPageResponse,
    NotificationPreferencesResponse,
    NotificationResponse,
    UpdateNotificationPreferencesRequest,
)
from app.modules.users.models import User
from app.modules.users.service import list_users_by_ids


async def queue_email(
    session: AsyncSession,
    *,
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    category: str,
    user_id: UUID | None = None,
    notification_id: UUID | None = None,
) -> EmailOutbox:
    message = EmailOutbox(
        recipient_email=recipient_email.lower(),
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        category=category,
        user_id=user_id,
        notification_id=notification_id,
        available_at=datetime.now(UTC),
    )
    session.add(message)
    await session.flush()
    return message


async def get_or_create_preferences(
    session: AsyncSession, user_id: UUID
) -> NotificationPreference:
    preferences = await repository.get_preferences(session, user_id)
    if preferences is None:
        preferences = NotificationPreference(user_id=user_id)
        session.add(preferences)
        await session.flush()
    return preferences


def _email_allowed(preferences: NotificationPreference, kind: NotificationKind) -> bool:
    if not preferences.email_enabled:
        return False
    if kind is NotificationKind.BET_CREATED:
        return preferences.bet_created_email
    if kind in {NotificationKind.BET_CLOSED, NotificationKind.RESOLUTION_REMINDER}:
        return preferences.bet_closed_email
    if kind is NotificationKind.BET_RESOLVED:
        return preferences.bet_resolved_email
    return preferences.bet_refunded_email


async def _visible_group_users(
    session: AsyncSession,
    bet: Bet,
    recipient_ids: set[UUID] | None,
) -> tuple[str, list[User]]:
    if bet.group_id is None:
        return "Group", []
    group = await groups_repository.get_group(session, bet.group_id)
    if group is None:
        return "Group", []
    memberships = await groups_repository.list_members(session, bet.group_id)
    allowed_ids = await bets_repository.get_visibility_user_ids(session, bet.id)
    visible_ids = {
        member.user_id
        for member in memberships
        if member.status is MembershipStatus.ACTIVE
        and (
            not allowed_ids
            or member.user_id in allowed_ids
            or member.user_id == bet.created_by
            or member.role is MemberRole.ADMIN
        )
        and (recipient_ids is None or member.user_id in recipient_ids)
    }
    return group.name, await list_users_by_ids(session, list(visible_ids))


def _event_copy(
    *,
    kind: NotificationKind,
    question: str,
    group_name: str,
    outcome_label: str | None,
) -> tuple[str, str]:
    if kind is NotificationKind.BET_CREATED:
        return "New group bet", f'{group_name}: "{question}" is now open.'
    if kind is NotificationKind.RESOLUTION_REMINDER:
        return "Resolve your group bet", f'Betting closed for "{question}". Pick the winner.'
    if kind is NotificationKind.BET_CLOSED:
        return "Group bet closed", f'Betting closed for "{question}". Waiting for resolution.'
    if kind is NotificationKind.BET_RESOLVED:
        return "Group bet resolved", f'"{question}" resolved as {outcome_label or "a winner"}.'
    return "Group bet refunded", f'"{question}" was cancelled. All stakes were refunded.'


async def notify_group_bet(
    session: AsyncSession,
    *,
    bet: Bet,
    kind: NotificationKind,
    settings: Settings,
    outcome_label: str | None = None,
    recipient_ids: set[UUID] | None = None,
) -> int:
    if bet.visibility is not BetVisibility.GROUP or bet.group_id is None:
        return 0
    group_name, users = await _visible_group_users(session, bet, recipient_ids)
    created = 0
    for user in users:
        user_kind = (
            NotificationKind.RESOLUTION_REMINDER
            if kind is NotificationKind.BET_CLOSED and user.id == bet.created_by
            else kind
        )
        if await repository.find_notification(
            session,
            user_id=user.id,
            kind=user_kind,
            bet_id=bet.id,
        ):
            continue
        title, body = _event_copy(
            kind=user_kind,
            question=bet.question,
            group_name=group_name,
            outcome_label=outcome_label,
        )
        notification = Notification(
            user_id=user.id,
            kind=user_kind,
            title=title,
            body=body,
            group_id=bet.group_id,
            bet_id=bet.id,
        )
        session.add(notification)
        await session.flush()
        preferences = await get_or_create_preferences(session, user.id)
        if _email_allowed(preferences, user_kind):
            link = f"{settings.frontend_url.rstrip('/')}/bets/{bet.id}"
            await queue_email(
                session,
                recipient_email=user.email,
                subject=f"BullyMarket — {title}",
                text_body=f"{body}\n\nOpen market: {link}",
                html_body=(
                    f"<p>{escape(body)}</p><p><a href=\"{escape(link)}\">Open market</a></p>"
                ),
                category=user_kind.value,
                user_id=user.id,
                notification_id=notification.id,
            )
        created += 1
    return created


async def list_user_notifications(
    session: AsyncSession,
    *,
    user_id: UUID,
    unread_only: bool,
    page: int,
    page_size: int,
) -> NotificationPageResponse:
    rows, total, unread = await repository.list_notifications(
        session,
        user_id=user_id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )
    return NotificationPageResponse(
        items=[NotificationResponse.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
        unread_count=unread,
    )


async def mark_notification_read(
    session: AsyncSession, *, notification_id: UUID, user_id: UUID
) -> Notification:
    notification = await repository.get_notification(session, notification_id, user_id)
    if notification is None:
        raise DomainError("notification_not_found", "Notification not found", 404)
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await session.flush()
    return notification


async def update_preferences(
    session: AsyncSession,
    *,
    user_id: UUID,
    payload: UpdateNotificationPreferencesRequest,
) -> NotificationPreferencesResponse:
    preferences = await get_or_create_preferences(session, user_id)
    for field, value in payload.model_dump().items():
        setattr(preferences, field, value)
    await session.flush()
    return NotificationPreferencesResponse.model_validate(preferences)

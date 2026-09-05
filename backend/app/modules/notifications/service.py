from dataclasses import dataclass
from datetime import UTC, datetime
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
from app.modules.notifications.templates import branded_email
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


@dataclass(frozen=True)
class EventCopy:
    title: str
    body: str
    subject: str
    email_title: str
    email_paragraphs: tuple[str, ...]
    action_label: str
    status_label: str


def _display_time(value: datetime) -> str:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(UTC).strftime("%d %b %Y, %H:%M UTC")


def _subject(prefix: str, question: str) -> str:
    return f"{prefix}: {question}"[:300]


def _event_copy(
    *,
    kind: NotificationKind,
    question: str,
    group_name: str,
    outcome_label: str | None,
    end_time: datetime,
) -> EventCopy:
    closes_at = _display_time(end_time)
    if kind is NotificationKind.BET_CREATED:
        return EventCopy(
            title=f"New bet in {group_name}",
            body=(
                f'“{question}” is open until {closes_at}. Review the live odds and place '
                "your prediction before betting closes."
            ),
            subject=_subject("New group bet", question),
            email_title="A new prediction is open",
            email_paragraphs=(
                f"A new market has been created in {group_name}.",
                "Open it to review the outcomes, check the latest odds, and make your pick.",
            ),
            action_label="View bet and odds",
            status_label="Open for predictions",
        )
    if kind is NotificationKind.RESOLUTION_REMINDER:
        return EventCopy(
            title="Your bet is ready for resolution",
            body=(
                f'Betting has closed for “{question}” in {group_name}. Confirm the final '
                "outcome so winning positions can be settled."
            ),
            subject=_subject("Action needed — resolve your bet", question),
            email_title="Your bet needs a result",
            email_paragraphs=(
                f"Betting has ended for your market in {group_name}.",
                "Open the bet, confirm what happened, and select the winning outcome to settle it.",
            ),
            action_label="Resolve this bet",
            status_label="Awaiting resolution",
        )
    if kind is NotificationKind.BET_CLOSED:
        return EventCopy(
            title=f"Betting closed in {group_name}",
            body=(
                f'“{question}” no longer accepts predictions. You’ll be notified when the '
                "winning outcome is confirmed."
            ),
            subject=_subject("Betting closed", question),
            email_title="Predictions are now closed",
            email_paragraphs=(
                f"The prediction window has ended for this market in {group_name}.",
                "No more trades can be placed. The market is now waiting for its final result.",
            ),
            action_label="Review closed bet",
            status_label="Awaiting resolution",
        )
    if kind is NotificationKind.BET_RESOLVED:
        winner = outcome_label or "the selected outcome"
        return EventCopy(
            title=f"Resolved: {winner}",
            body=(
                f'“{question}” in {group_name} resolved as {winner}. Winning positions '
                "have been paid automatically."
            ),
            subject=_subject(f"Resolved — {winner}", question),
            email_title="The result is in",
            email_paragraphs=(
                f"The market in {group_name} has been resolved as {winner}.",
                "All winning positions have been settled automatically. Open the bet to review it.",
            ),
            action_label="Review result",
            status_label="Resolved",
        )
    return EventCopy(
        title=f"Bet cancelled in {group_name}",
        body=(
            f'“{question}” was cancelled. Any points committed to this market were returned '
            "automatically."
        ),
        subject=_subject("Bet cancelled and refunded", question),
        email_title="This bet was cancelled",
        email_paragraphs=(
            f"The market in {group_name} has been cancelled.",
            "Eligible stakes were returned automatically. No action is required from you.",
        ),
        action_label="Review refund",
        status_label="Cancelled and refunded",
    )


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
        copy = _event_copy(
            kind=user_kind,
            question=bet.question,
            group_name=group_name,
            outcome_label=outcome_label,
            end_time=bet.end_time,
        )
        notification = Notification(
            user_id=user.id,
            kind=user_kind,
            title=copy.title,
            body=copy.body,
            group_id=bet.group_id,
            bet_id=bet.id,
        )
        session.add(notification)
        await session.flush()
        preferences = await get_or_create_preferences(session, user.id)
        if _email_allowed(preferences, user_kind):
            details = [
                ("Group", group_name),
                ("Market", bet.question),
                ("Status", copy.status_label),
                ("Betting closed", _display_time(bet.end_time)),
            ]
            if user_kind is NotificationKind.BET_RESOLVED and outcome_label:
                details.append(("Winning outcome", outcome_label))
            email_content = branded_email(
                frontend_url=settings.frontend_url,
                subject=copy.subject,
                preheader=copy.body,
                eyebrow=user_kind.value.replace("_", " "),
                title=copy.email_title,
                greeting=f"Hi {user.display_name},",
                paragraphs=copy.email_paragraphs,
                details=tuple(details),
                action_label=copy.action_label,
                action_path=f"/bets/{bet.id}",
                note=(
                    "You received this because you are a member of this group and have "
                    "email notifications enabled for this event."
                ),
            )
            await queue_email(
                session,
                recipient_email=user.email,
                subject=email_content.subject,
                text_body=email_content.text,
                html_body=email_content.html,
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

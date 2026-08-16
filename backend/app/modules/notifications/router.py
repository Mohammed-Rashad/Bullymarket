from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, SessionDependency
from app.modules.notifications import repository
from app.modules.notifications.schemas import (
    MarkAllReadResponse,
    NotificationPageResponse,
    NotificationPreferencesResponse,
    NotificationResponse,
    UpdateNotificationPreferencesRequest,
)
from app.modules.notifications.service import (
    get_or_create_preferences,
    list_user_notifications,
    mark_notification_read,
    update_preferences,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])
PageNumber = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=NotificationPageResponse)
async def list_notifications_route(
    session: SessionDependency,
    current_user: CurrentUser,
    unread_only: bool = False,
    page: PageNumber = 1,
    page_size: PageSize = 20,
) -> NotificationPageResponse:
    return await list_user_notifications(
        session,
        user_id=current_user.id,
        unread_only=unread_only,
        page=page,
        page_size=page_size,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read_route(
    notification_id: UUID,
    session: SessionDependency,
    current_user: CurrentUser,
) -> NotificationResponse:
    notification = await mark_notification_read(
        session,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(notification)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read_route(
    session: SessionDependency,
    current_user: CurrentUser,
) -> MarkAllReadResponse:
    return MarkAllReadResponse(updated=await repository.mark_all_read(session, current_user.id))


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def preferences_route(
    session: SessionDependency,
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    preferences = await get_or_create_preferences(session, current_user.id)
    return NotificationPreferencesResponse.model_validate(preferences)


@router.patch("/preferences", response_model=NotificationPreferencesResponse)
async def update_preferences_route(
    payload: UpdateNotificationPreferencesRequest,
    session: SessionDependency,
    current_user: CurrentUser,
) -> NotificationPreferencesResponse:
    return await update_preferences(
        session,
        user_id=current_user.id,
        payload=payload,
    )

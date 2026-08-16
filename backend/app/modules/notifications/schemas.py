from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.notifications.models import NotificationKind


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: NotificationKind
    title: str
    body: str
    group_id: UUID | None
    bet_id: UUID | None
    created_at: datetime
    read_at: datetime | None


class NotificationPageResponse(BaseModel):
    items: list[NotificationResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
    unread_count: int


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_enabled: bool
    bet_created_email: bool
    bet_closed_email: bool
    bet_resolved_email: bool
    bet_refunded_email: bool


class UpdateNotificationPreferencesRequest(NotificationPreferencesResponse):
    pass


class MarkAllReadResponse(BaseModel):
    updated: int

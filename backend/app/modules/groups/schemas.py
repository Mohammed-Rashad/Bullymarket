from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.groups.models import MemberRole, MembershipStatus
from app.modules.media.service import is_managed_image_url


class CreateGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if not is_managed_image_url(value):
            raise ValueError("image_url must reference an uploaded image")
        return value


class JoinGroupRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=32)


class UpdateMemberRoleRequest(BaseModel):
    role: MemberRole


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    image_url: str | None
    invite_code: str | None
    created_by: UUID
    created_at: datetime
    role: MemberRole
    membership_status: MembershipStatus
    pending_settlement: bool = False


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str
    role: MemberRole
    status: MembershipStatus
    joined_at: datetime
    removed_at: datetime | None

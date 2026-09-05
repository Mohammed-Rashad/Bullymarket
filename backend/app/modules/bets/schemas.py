from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.bets.models import BetStatus, BetVisibility, PricingMethod
from app.modules.media.service import is_managed_image_url


class CreateBetRequest(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    image_url: str | None = Field(default=None, max_length=500)
    end_time: datetime
    outcome_labels: list[str]
    visible_to_user_ids: list[UUID] | None = None
    b_liquidity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=20,
        decimal_places=8,
    )

    @field_validator("outcome_labels")
    @classmethod
    def validate_outcomes(cls, labels: list[str]) -> list[str]:
        cleaned = [label.strip() for label in labels]
        if len(cleaned) != 2:
            raise ValueError("v1 bets require exactly two outcomes")
        if any(not label or len(label) > 80 for label in cleaned):
            raise ValueError("outcome labels must contain 1 to 80 characters")
        if cleaned[0].casefold() == cleaned[1].casefold():
            raise ValueError("outcome labels must be distinct")
        return cleaned

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if not is_managed_image_url(value):
            raise ValueError("image_url must reference an uploaded image")
        return value


class EditEndTimeRequest(BaseModel):
    end_time: datetime


class OutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    display_order: int
    pool_shares: Decimal
    price: Decimal


class BetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID | None
    created_by: UUID
    question: str
    description: str | None
    image_url: str | None
    visibility: BetVisibility
    status: BetStatus
    end_time: datetime
    resolved_outcome_id: UUID | None
    resolved_at: datetime | None
    created_at: datetime
    pricing_method: PricingMethod
    b_liquidity: Decimal | None
    q_yes: Decimal | None
    q_no: Decimal | None
    house_reserve: Decimal
    house_cash_balance: Decimal
    house_profit_loss: Decimal | None
    outcomes: list[OutcomeResponse]


class PaginatedBetsResponse(BaseModel):
    items: list[BetResponse]
    page: int
    page_size: int
    total: int
    total_pages: int


class BetEditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    edited_by: UUID
    edit_type: str
    old_value: str
    new_value: str
    created_at: datetime


class CancellationResponse(BaseModel):
    bet_id: UUID
    refunded_users: int
    refunded_points: Decimal
    cancelled_at: datetime

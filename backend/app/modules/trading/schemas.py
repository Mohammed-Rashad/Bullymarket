from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuyRequest(BaseModel):
    outcome_id: UUID
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=8)


class BuyPreviewResponse(BaseModel):
    outcome_id: UUID
    amount: Decimal
    shares_out: Decimal
    price_yes_after: Decimal
    price_no_after: Decimal


class TradeResponse(BuyPreviewResponse):
    remaining_balance: Decimal
    position_shares: Decimal


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outcome_id: UUID
    shares: Decimal
    points_spent: Decimal


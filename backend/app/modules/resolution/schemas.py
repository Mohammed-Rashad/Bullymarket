from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResolveRequest(BaseModel):
    outcome_id: UUID


class ResolutionResponse(BaseModel):
    bet_id: UUID
    outcome_id: UUID
    is_correction: bool
    affected_users: int
    total_payout: Decimal
    house_profit_loss: Decimal | None
    resolved_at: datetime


class ResolutionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    outcome_id: UUID
    resolved_by: UUID
    is_correction: bool
    created_at: datetime

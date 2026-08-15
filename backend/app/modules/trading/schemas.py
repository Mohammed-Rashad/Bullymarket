from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.trading.models import TradeSide


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


class LmsrPriceResponse(BaseModel):
    bet_id: UUID
    price_yes: Decimal
    price_no: Decimal
    q_yes: Decimal
    q_no: Decimal
    b_liquidity: Decimal


class LmsrTradeRequest(BaseModel):
    side: TradeSide
    shares: Decimal = Field(max_digits=20, decimal_places=8)

    @field_validator("shares")
    @classmethod
    def shares_must_be_nonzero(cls, shares: Decimal) -> Decimal:
        if shares == 0:
            raise ValueError("shares cannot be zero")
        return shares


class LmsrQuoteResponse(LmsrPriceResponse):
    side: TradeSide
    delta_shares: Decimal
    cost: Decimal
    average_price: Decimal
    q_yes_after: Decimal
    q_no_after: Decimal
    price_yes_after: Decimal
    price_no_after: Decimal


class LmsrTradeResponse(LmsrQuoteResponse):
    trade_id: UUID
    outcome_id: UUID
    remaining_balance: Decimal
    position_shares: Decimal
    house_cash_flow: Decimal


class TradeAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bet_id: UUID
    user_id: UUID
    outcome_id: UUID
    sequence: int
    side: TradeSide
    delta_shares: Decimal
    cost: Decimal
    house_cash_flow: Decimal
    q_yes_after: Decimal
    q_no_after: Decimal
    created_at: datetime

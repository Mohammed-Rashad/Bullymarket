from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.house.models import HouseLedgerEntryType


class HouseSummaryResponse(BaseModel):
    scope: Literal["bet", "group", "global"]
    bet_id: UUID | None = None
    group_id: UUID | None = None
    markets: int
    open_markets: int
    trades: int
    reserved_exposure: Decimal
    trade_cash_flow: Decimal
    current_cash_balance: Decimal
    realized_profit_loss: Decimal


class HouseLedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bet_id: UUID
    group_id: UUID | None
    trade_id: UUID | None
    sequence: int
    entry_type: HouseLedgerEntryType
    cash_delta: Decimal
    reserve_delta: Decimal
    realized_pnl_delta: Decimal
    created_at: datetime

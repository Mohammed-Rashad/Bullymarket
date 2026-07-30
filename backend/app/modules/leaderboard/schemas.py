from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class LeaderboardWindow(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    display_name: str
    net_profit_loss: Decimal


class LeaderboardResponse(BaseModel):
    scope: str
    window: LeaderboardWindow
    entries: list[LeaderboardEntry]


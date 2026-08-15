from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class LedgerEntryType(StrEnum):
    REFILL = "refill"
    BET_PLACED = "bet_placed"
    PAYOUT = "payout"
    RESOLUTION_REVERSAL = "resolution_reversal"
    BET_REFUND = "bet_refund"
    # LMSR trades use the historical database value so old ledger queries and
    # PostgreSQL enum rows remain backward-compatible. Signed amounts distinguish
    # buys (negative for the user) from sells (positive for the user).
    MARKET_TRADE = "bet_placed"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_bet_user_type", "bet_id", "user_id", "entry_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(
            LedgerEntryType,
            name="ledger_entry_type",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    bet_id: Mapped[UUID | None] = mapped_column(ForeignKey("bets.id"))
    related_ledger_entry_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ledger_entries.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

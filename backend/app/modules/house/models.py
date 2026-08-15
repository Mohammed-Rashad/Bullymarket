from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class HouseLedgerEntryType(StrEnum):
    RESERVE = "reserve"
    TRADE = "trade"
    PAYOUT = "payout"
    RESOLUTION_REVERSAL = "resolution_reversal"
    REFUND = "refund"
    RESERVE_RELEASE = "reserve_release"
    PNL_ADJUSTMENT = "pnl_adjustment"


class HouseLedgerEntry(Base):
    __tablename__ = "house_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "cash_delta <> 0 OR reserve_delta <> 0 OR realized_pnl_delta <> 0",
            name="has_financial_effect",
        ),
        Index("ix_house_ledger_bet_created", "bet_id", "created_at"),
        Index("ix_house_ledger_group_created", "group_id", "created_at"),
        Index("ix_house_ledger_trade", "trade_id"),
        UniqueConstraint(
            "bet_id",
            "sequence",
            name="uq_house_ledger_entries_bet_sequence",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id"))
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("groups.id"))
    trade_id: Mapped[UUID | None] = mapped_column(ForeignKey("trades.id"))
    sequence: Mapped[int]
    entry_type: Mapped[HouseLedgerEntryType] = mapped_column(
        Enum(
            HouseLedgerEntryType,
            name="house_ledger_entry_type",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    cash_delta: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal(0))
    reserve_delta: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), default=Decimal(0)
    )
    realized_pnl_delta: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), default=Decimal(0)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

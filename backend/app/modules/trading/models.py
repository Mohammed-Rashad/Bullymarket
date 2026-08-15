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


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "bet_id",
            "outcome_id",
            name="uq_positions_user_bet_outcome",
        ),
        CheckConstraint("shares >= 0", name="shares_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id"))
    outcome_id: Mapped[UUID] = mapped_column(ForeignKey("outcomes.id"))
    shares: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    points_spent: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TradeSide(StrEnum):
    YES = "yes"
    NO = "no"


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint("delta_shares <> 0", name="delta_shares_nonzero"),
        CheckConstraint("q_yes_after >= 0", name="q_yes_after_nonnegative"),
        CheckConstraint("q_no_after >= 0", name="q_no_after_nonnegative"),
        Index("ix_trades_bet_created", "bet_id", "created_at"),
        Index("ix_trades_user_created", "user_id", "created_at"),
        UniqueConstraint("bet_id", "sequence", name="uq_trades_bet_sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    outcome_id: Mapped[UUID] = mapped_column(ForeignKey("outcomes.id"))
    sequence: Mapped[int]
    side: Mapped[TradeSide] = mapped_column(
        Enum(
            TradeSide,
            name="trade_side",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    delta_shares: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    cost: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    house_cash_flow: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    q_yes_after: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    q_no_after: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

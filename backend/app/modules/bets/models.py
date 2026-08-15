from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BetVisibility(StrEnum):
    GROUP = "group"
    PUBLIC = "public"


class BetStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class PricingMethod(StrEnum):
    CPMM = "cpmm"
    LMSR = "lmsr"


class BetEditType(StrEnum):
    END_TIME = "end_time"


class Bet(Base):
    __tablename__ = "bets"
    __table_args__ = (
        CheckConstraint(
            "(visibility = 'group' AND group_id IS NOT NULL) OR "
            "(visibility = 'public' AND group_id IS NULL)",
            name="scope_matches_group",
        ),
        UniqueConstraint("id", "group_id", name="uq_bets_id_group_id"),
        Index("ix_bets_group_status_resolved", "group_id", "status", "resolved_at"),
        Index("ix_bets_visibility_status_resolved", "visibility", "status", "resolved_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("groups.id"))
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    question: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[BetVisibility] = mapped_column(
        Enum(
            BetVisibility,
            name="bet_visibility",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus, name="bet_status", values_callable=lambda enum: [e.value for e in enum]),
        default=BetStatus.OPEN,
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_outcome_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "outcomes.id",
            name="fk_bets_resolved_outcome_id_outcomes",
            use_alter=True,
        )
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    liquidity_seed: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    pricing_method: Mapped[PricingMethod] = mapped_column(
        Enum(
            PricingMethod,
            name="pricing_method",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=PricingMethod.LMSR,
    )
    b_liquidity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    q_yes: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    q_no: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    house_reserve: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal(0))
    house_cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(24, 8), default=Decimal(0)
    )
    house_profit_loss: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        UniqueConstraint("bet_id", "display_order", name="uq_outcomes_bet_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(80))
    pool_shares: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    display_order: Mapped[int] = mapped_column(Integer)


class BetVisibilityOverride(Base):
    __tablename__ = "bet_visibility_overrides"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bet_id", "group_id"],
            ["bets.id", "bets.group_id"],
            name="fk_visibility_override_bet_group",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["group_id", "user_id"],
            ["group_members.group_id", "group_members.user_id"],
            name="fk_visibility_override_membership",
            ondelete="CASCADE",
        ),
        UniqueConstraint("bet_id", "user_id", name="uq_visibility_override_bet_user"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID]
    group_id: Mapped[UUID]
    user_id: Mapped[UUID]


class BetEditEvent(Base):
    __tablename__ = "bet_edit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id", ondelete="CASCADE"))
    edited_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    edit_type: Mapped[BetEditType] = mapped_column(
        Enum(
            BetEditType,
            name="bet_edit_type",
            values_callable=lambda enum: [e.value for e in enum],
        )
    )
    old_value: Mapped[str] = mapped_column(Text)
    new_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

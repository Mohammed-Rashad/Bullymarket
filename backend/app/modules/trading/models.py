from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint, func
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
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id"))
    outcome_id: Mapped[UUID] = mapped_column(ForeignKey("outcomes.id"))
    shares: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    points_spent: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ResolutionEvent(Base):
    __tablename__ = "resolution_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    bet_id: Mapped[UUID] = mapped_column(ForeignKey("bets.id"))
    outcome_id: Mapped[UUID] = mapped_column(ForeignKey("outcomes.id"))
    resolved_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    is_correction: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


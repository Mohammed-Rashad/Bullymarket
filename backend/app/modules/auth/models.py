from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class VerificationPurpose(StrEnum):
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"


class VerificationChallenge(Base):
    __tablename__ = "verification_challenges"
    __table_args__ = (
        Index(
            "ix_verification_challenges_lookup",
            "email",
            "purpose",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    purpose: Mapped[VerificationPurpose] = mapped_column(
        Enum(
            VerificationPurpose,
            name="verification_purpose",
            values_callable=lambda enum: [entry.value for entry in enum],
        )
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    display_name: Mapped[str | None] = mapped_column(String(80))
    pending_password_hash: Mapped[str | None] = mapped_column(String(512))
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

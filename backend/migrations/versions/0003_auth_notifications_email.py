"""Add verification challenges, notifications, preferences, and email outbox.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

verification_purpose = sa.Enum(
    "registration", "password_reset", name="verification_purpose"
)
notification_kind = sa.Enum(
    "bet_created",
    "bet_closed",
    "resolution_reminder",
    "bet_resolved",
    "bet_refunded",
    name="notification_kind",
)
email_outbox_status = sa.Enum("pending", "sent", "failed", name="email_outbox_status")


def upgrade() -> None:
    op.create_table(
        "verification_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", verification_purpose, nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("display_name", sa.String(80)),
        sa.Column("pending_password_hash", sa.String(512)),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_verification_challenges_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_challenges"),
    )
    op.create_index(
        "ix_verification_challenges_email",
        "verification_challenges",
        ["email"],
    )
    op.create_index(
        "ix_verification_challenges_lookup",
        "verification_challenges",
        ["email", "purpose", "created_at"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("bet_created_email", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("bet_closed_email", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("bet_resolved_email", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("bet_refunded_email", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_notification_preferences"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", notification_kind, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("group_id", sa.Uuid()),
        sa.Column("bet_id", sa.Uuid()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name="fk_notifications_group_id_groups", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_notifications_bet_id_bets", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.UniqueConstraint(
            "user_id", "kind", "bet_id", name="uq_notifications_user_kind_bet"
        ),
    )
    op.create_index(
        "ix_notifications_user_created", "notifications", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_notifications_user_read", "notifications", ["user_id", "read_at"]
    )

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("notification_id", sa.Uuid()),
        sa.Column(
            "status",
            email_outbox_status,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_email_outbox_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_email_outbox_notification_id_notifications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_email_outbox"),
        sa.UniqueConstraint("notification_id", name="uq_email_outbox_notification_id"),
    )
    op.create_index(
        "ix_email_outbox_delivery",
        "email_outbox",
        ["status", "available_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_outbox_delivery", table_name="email_outbox")
    op.drop_table("email_outbox")
    op.drop_index("ix_notifications_user_read", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
    op.drop_index("ix_verification_challenges_lookup", table_name="verification_challenges")
    op.drop_index("ix_verification_challenges_email", table_name="verification_challenges")
    op.drop_table("verification_challenges")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        email_outbox_status.drop(bind, checkfirst=True)
        notification_kind.drop(bind, checkfirst=True)
        verification_purpose.drop(bind, checkfirst=True)

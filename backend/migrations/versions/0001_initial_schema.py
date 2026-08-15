"""Create the initial BullyMarket schema.

Revision ID: 0001
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

member_role = sa.Enum("member", "admin", name="member_role")
membership_status = sa.Enum("active", "removed", name="membership_status")
bet_visibility = sa.Enum("group", "public", name="bet_visibility")
bet_status = sa.Enum("open", "closed", "resolved", "cancelled", name="bet_status")
bet_edit_type = sa.Enum("end_time", name="bet_edit_type")
ledger_entry_type = sa.Enum(
    "refill",
    "bet_placed",
    "payout",
    "resolution_reversal",
    "bet_refund",
    name="ledger_entry_type",
)


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_refill_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("invite_code", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_groups_created_by_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_groups"),
    )
    op.create_index(
        "ix_groups_invite_code",
        "groups",
        ["invite_code"],
        unique=True,
    )

    op.create_table(
        "group_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", member_role, nullable=False),
        sa.Column(
            "status",
            membership_status,
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name="fk_group_members_group_id_groups",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_group_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_group_members"),
        sa.UniqueConstraint(
            "group_id", "user_id", name="uq_group_members_group_user"
        ),
    )

    resolved_outcome_foreign_key: tuple[sa.ForeignKeyConstraint, ...] = ()
    if dialect_name == "sqlite":
        resolved_outcome_foreign_key = (
            sa.ForeignKeyConstraint(
                ["resolved_outcome_id"],
                ["outcomes.id"],
                name="fk_bets_resolved_outcome_id_outcomes",
            ),
        )

    op.create_table(
        "bets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", bet_visibility, nullable=False),
        sa.Column(
            "status",
            bet_status,
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_outcome_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("liquidity_seed", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(visibility = 'group' AND group_id IS NOT NULL) OR "
            "(visibility = 'public' AND group_id IS NULL)",
            name="scope_matches_group",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_bets_created_by_users"
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name="fk_bets_group_id_groups"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"], name="fk_bets_resolved_by_users"
        ),
        *resolved_outcome_foreign_key,
        sa.PrimaryKeyConstraint("id", name="pk_bets"),
        sa.UniqueConstraint("id", "group_id", name="uq_bets_id_group_id"),
    )

    op.create_table(
        "outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("pool_shares", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["bet_id"],
            ["bets.id"],
            name="fk_outcomes_bet_id_bets",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_outcomes"),
        sa.UniqueConstraint("bet_id", "display_order", name="uq_outcomes_bet_order"),
    )
    if dialect_name != "sqlite":
        op.create_foreign_key(
            "fk_bets_resolved_outcome_id_outcomes",
            "bets",
            "outcomes",
            ["resolved_outcome_id"],
            ["id"],
        )

    position_check_constraints: tuple[sa.CheckConstraint, ...] = ()
    if dialect_name == "sqlite":
        position_check_constraints = (
            sa.CheckConstraint(
                "shares >= 0",
                name="shares_nonnegative",
            ),
        )

    op.create_table(
        "positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("shares", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("points_spent", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        *position_check_constraints,
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_positions_bet_id_bets"
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"], ["outcomes.id"], name="fk_positions_outcome_id_outcomes"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_positions_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_positions"),
        sa.UniqueConstraint(
            "user_id", "bet_id", "outcome_id", name="uq_positions_user_bet_outcome"
        ),
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("entry_type", ledger_entry_type, nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=True),
        sa.Column("related_ledger_entry_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_ledger_entries_bet_id_bets"
        ),
        sa.ForeignKeyConstraint(
            ["related_ledger_entry_id"],
            ["ledger_entries.id"],
            name="fk_ledger_entries_related_ledger_entry_id_ledger_entries",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ledger_entries_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
    )

    op.create_table(
        "resolution_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=False),
        sa.Column("is_correction", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_resolution_events_bet_id_bets"
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["outcomes.id"],
            name="fk_resolution_events_outcome_id_outcomes",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_resolution_events_resolved_by_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_resolution_events"),
    )

    op.create_table(
        "bet_visibility_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["bet_id", "group_id"],
            ["bets.id", "bets.group_id"],
            name="fk_visibility_override_bet_group",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id", "user_id"],
            ["group_members.group_id", "group_members.user_id"],
            name="fk_visibility_override_membership",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bet_visibility_overrides"),
        sa.UniqueConstraint(
            "bet_id", "user_id", name="uq_visibility_override_bet_user"
        ),
    )

    op.create_table(
        "bet_edit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("edited_by", sa.Uuid(), nullable=False),
        sa.Column("edit_type", bet_edit_type, nullable=False),
        sa.Column("old_value", sa.Text(), nullable=False),
        sa.Column("new_value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"],
            ["bets.id"],
            name="fk_bet_edit_events_bet_id_bets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["edited_by"], ["users.id"], name="fk_bet_edit_events_edited_by_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bet_edit_events"),
    )

    op.create_index(
        "ix_bets_group_status_resolved",
        "bets",
        ["group_id", "status", "resolved_at"],
    )
    op.create_index(
        "ix_bets_visibility_status_resolved",
        "bets",
        ["visibility", "status", "resolved_at"],
    )
    op.create_index(
        "ix_ledger_bet_user_type",
        "ledger_entries",
        ["bet_id", "user_id", "entry_type"],
    )


def downgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        op.execute("PRAGMA foreign_keys=OFF")

    op.drop_index("ix_ledger_bet_user_type", table_name="ledger_entries")
    op.drop_index("ix_bets_visibility_status_resolved", table_name="bets")
    op.drop_index("ix_bets_group_status_resolved", table_name="bets")
    op.drop_table("bet_edit_events")
    op.drop_table("bet_visibility_overrides")
    op.drop_table("resolution_events")
    op.drop_table("ledger_entries")
    op.drop_table("positions")
    if dialect_name != "sqlite":
        op.drop_constraint(
            "fk_bets_resolved_outcome_id_outcomes",
            "bets",
            type_="foreignkey",
        )
    op.drop_table("outcomes")
    op.drop_table("bets")
    op.drop_table("group_members")
    op.drop_index("ix_groups_invite_code", table_name="groups")
    op.drop_table("groups")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    ledger_entry_type.drop(bind, checkfirst=True)
    bet_edit_type.drop(bind, checkfirst=True)
    bet_status.drop(bind, checkfirst=True)
    bet_visibility.drop(bind, checkfirst=True)
    membership_status.drop(bind, checkfirst=True)
    member_role.drop(bind, checkfirst=True)
    if dialect_name == "sqlite":
        op.execute("PRAGMA foreign_keys=ON")

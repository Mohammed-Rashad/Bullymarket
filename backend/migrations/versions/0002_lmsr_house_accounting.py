"""Add LMSR state, trade audit, and house accounting.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pricing_method = sa.Enum("cpmm", "lmsr", name="pricing_method")
trade_side = sa.Enum("yes", "no", name="trade_side")
house_ledger_entry_type = sa.Enum(
    "reserve",
    "trade",
    "payout",
    "resolution_reversal",
    "refund",
    "reserve_release",
    "pnl_adjustment",
    name="house_ledger_entry_type",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        pricing_method.create(bind, checkfirst=True)

    op.add_column(
        "bets",
        sa.Column(
            "pricing_method",
            pricing_method,
            server_default=sa.text("'cpmm'"),
            nullable=False,
        )
    )
    op.add_column("bets", sa.Column("b_liquidity", sa.Numeric(24, 8)))
    op.add_column("bets", sa.Column("q_yes", sa.Numeric(24, 8)))
    op.add_column("bets", sa.Column("q_no", sa.Numeric(24, 8)))
    op.add_column(
        "bets",
        sa.Column(
            "house_reserve",
            sa.Numeric(24, 8),
            server_default=sa.text("0"),
            nullable=False,
        )
    )
    op.add_column(
        "bets",
        sa.Column(
            "house_cash_balance",
            sa.Numeric(24, 8),
            server_default=sa.text("0"),
            nullable=False,
        )
    )
    op.add_column("bets", sa.Column("house_profit_loss", sa.Numeric(24, 8)))

    if bind.dialect.name == "postgresql":
        op.create_check_constraint(
            "shares_nonnegative",
            "positions",
            "shares >= 0",
        )

    op.create_table(
        "trades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("outcome_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("side", trade_side, nullable=False),
        sa.Column("delta_shares", sa.Numeric(24, 8), nullable=False),
        sa.Column("cost", sa.Numeric(24, 8), nullable=False),
        sa.Column("house_cash_flow", sa.Numeric(24, 8), nullable=False),
        sa.Column("q_yes_after", sa.Numeric(24, 8), nullable=False),
        sa.Column("q_no_after", sa.Numeric(24, 8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "delta_shares <> 0",
            name="delta_shares_nonzero",
        ),
        sa.CheckConstraint(
            "q_yes_after >= 0",
            name="q_yes_after_nonnegative",
        ),
        sa.CheckConstraint(
            "q_no_after >= 0",
            name="q_no_after_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_trades_bet_id_bets"
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"], ["outcomes.id"], name="fk_trades_outcome_id_outcomes"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_trades_user_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trades"),
        sa.UniqueConstraint("bet_id", "sequence", name="uq_trades_bet_sequence"),
    )
    op.create_index("ix_trades_bet_created", "trades", ["bet_id", "created_at"])
    op.create_index("ix_trades_user_created", "trades", ["user_id", "created_at"])

    op.create_table(
        "house_ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bet_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid()),
        sa.Column("trade_id", sa.Uuid()),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("entry_type", house_ledger_entry_type, nullable=False),
        sa.Column(
            "cash_delta", sa.Numeric(24, 8), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "reserve_delta",
            sa.Numeric(24, 8),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "realized_pnl_delta",
            sa.Numeric(24, 8),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "cash_delta <> 0 OR reserve_delta <> 0 OR realized_pnl_delta <> 0",
            name="has_financial_effect",
        ),
        sa.ForeignKeyConstraint(
            ["bet_id"], ["bets.id"], name="fk_house_ledger_entries_bet_id_bets"
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name="fk_house_ledger_entries_group_id_groups"
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], name="fk_house_ledger_entries_trade_id_trades"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_house_ledger_entries"),
        sa.UniqueConstraint(
            "bet_id",
            "sequence",
            name="uq_house_ledger_entries_bet_sequence",
        ),
    )
    op.create_index(
        "ix_house_ledger_bet_created",
        "house_ledger_entries",
        ["bet_id", "created_at"],
    )
    op.create_index(
        "ix_house_ledger_group_created",
        "house_ledger_entries",
        ["group_id", "created_at"],
    )
    op.create_index(
        "ix_house_ledger_trade",
        "house_ledger_entries",
        ["trade_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_house_ledger_trade", table_name="house_ledger_entries")
    op.drop_index("ix_house_ledger_group_created", table_name="house_ledger_entries")
    op.drop_index("ix_house_ledger_bet_created", table_name="house_ledger_entries")
    op.drop_table("house_ledger_entries")
    op.drop_index("ix_trades_user_created", table_name="trades")
    op.drop_index("ix_trades_bet_created", table_name="trades")
    op.drop_table("trades")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "ck_positions_shares_nonnegative",
            "positions",
            type_="check",
        )

    op.drop_column("bets", "house_profit_loss")
    op.drop_column("bets", "house_cash_balance")
    op.drop_column("bets", "house_reserve")
    op.drop_column("bets", "q_no")
    op.drop_column("bets", "q_yes")
    op.drop_column("bets", "b_liquidity")
    op.drop_column("bets", "pricing_method")

    if bind.dialect.name == "postgresql":
        house_ledger_entry_type.drop(bind, checkfirst=True)
        trade_side.drop(bind, checkfirst=True)
        pricing_method.drop(bind, checkfirst=True)

"""Add optional images to groups and bets.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("image_url", sa.String(500)))
    op.add_column("bets", sa.Column("image_url", sa.String(500)))


def downgrade() -> None:
    op.drop_column("bets", "image_url")
    op.drop_column("groups", "image_url")

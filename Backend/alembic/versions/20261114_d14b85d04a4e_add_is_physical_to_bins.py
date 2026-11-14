"""add is_physical to bins

Revision ID: d14b85d04a4e
Revises: bf84ef2bd12d
Create Date: 2026-11-14 16:19:30.801239
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d14b85d04a4e"
down_revision: str | None = "bf84ef2bd12d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bins",
        sa.Column("is_physical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("bins", "is_physical")

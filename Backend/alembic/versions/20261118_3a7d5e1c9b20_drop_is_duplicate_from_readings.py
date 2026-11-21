"""drop is_duplicate from readings

Duplicates are never saved in readings, so the flag could never be true.
They are now saved in rejected_readings with reason "duplicate" (contract v1.2).

Revision ID: 3a7d5e1c9b20
Revises: 8e4b2d6a1f37
Create Date: 2026-11-18 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3a7d5e1c9b20"
down_revision: str | None = "8e4b2d6a1f37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("readings", "is_duplicate")


def downgrade() -> None:
    op.add_column(
        "readings",
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

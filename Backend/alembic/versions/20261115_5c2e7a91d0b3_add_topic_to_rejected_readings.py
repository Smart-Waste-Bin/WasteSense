"""add topic to rejected_readings

Revision ID: 5c2e7a91d0b3
Revises: d14b85d04a4e
Create Date: 2026-11-15 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5c2e7a91d0b3"
down_revision: str | None = "d14b85d04a4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rejected_readings", sa.Column("topic", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rejected_readings", "topic")

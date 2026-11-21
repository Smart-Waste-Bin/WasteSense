"""user profile photo (AUTH-03)

photo_key: where the user's profile photo is stored (local file name or S3 key).

Revision ID: 9c41d7e2b5a6
Revises: 3a7d5e1c9b20
Create Date: 2026-11-21 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c41d7e2b5a6"
down_revision: str | None = "3a7d5e1c9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("photo_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "photo_key")

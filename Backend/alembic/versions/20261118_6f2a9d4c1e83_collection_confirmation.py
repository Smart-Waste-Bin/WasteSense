"""collection confirmation (BE-08)

confirmed_at: when a sensor reading confirmed the bin was emptied.
unconfirmed_at: when the 30-minute check flagged it as not confirmed.
At most one collection per route stop, and an index to find a bin's recent collections.

Revision ID: 6f2a9d4c1e83
Revises: 3a7d5e1c9b20
Create Date: 2026-11-18 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6f2a9d4c1e83"
down_revision: str | None = "3a7d5e1c9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("collections", sa.Column("confirmed_at", sa.DateTime(timezone=True)))
    op.add_column("collections", sa.Column("unconfirmed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_collections_bin_id_emptied_at", "collections", ["bin_id", "emptied_at"])
    op.create_index(
        "uq_collections_stop_id",
        "collections",
        ["stop_id"],
        unique=True,
        postgresql_where=sa.text("stop_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_collections_stop_id", table_name="collections")
    op.drop_index("ix_collections_bin_id_emptied_at", table_name="collections")
    op.drop_column("collections", "unconfirmed_at")
    op.drop_column("collections", "confirmed_at")

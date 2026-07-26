"""drop outbox_events

Revision ID: 0896cce46c31
Revises: 4a6d5897183b
Create Date: 2026-07-26 07:24:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0896cce46c31"
down_revision: str | Sequence[str] | None = "4a6d5897183b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("outbox_events")


def downgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

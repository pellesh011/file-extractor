"""add worker fields and downloaded_files table

Revision ID: 9d7c4a3b1e2f
Revises: 0896cce46c31
Create Date: 2026-07-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9d7c4a3b1e2f"
down_revision: str | Sequence[str] | None = "0896cce46c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "download_tasks",
        sa.Column("worker_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "download_tasks",
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "download_tasks",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "download_tasks",
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "download_tasks",
        sa.Column("block_reason", sa.String(255), nullable=True),
    )

    op.create_table(
        "downloaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("download_tasks.id"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("hash", sa.String(64), nullable=True),
        sa.UniqueConstraint("task_id", "file_name", name="uq_task_file"),
    )


def downgrade() -> None:
    op.drop_table("downloaded_files")
    op.drop_column("download_tasks", "block_reason")
    op.drop_column("download_tasks", "blocked_until")
    op.drop_column("download_tasks", "attempts")
    op.drop_column("download_tasks", "last_heartbeat")
    op.drop_column("download_tasks", "worker_id")

"""initial

Revision ID: 4a6d5897183b
Revises:
Create Date: 2026-07-24 13:00:12.196915

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4a6d5897183b"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("hash", sa.String(64), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "download_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CREATED"),
        sa.Column("received_files", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("processed_files", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
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


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("download_tasks")
    op.drop_table("files")

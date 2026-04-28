"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True)),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("description", sa.Text),
        sa.Column("is_billable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("billing_rate_id", postgresql.UUID(as_uuid=True)),
        sa.Column("billed_amount", sa.Numeric(10, 2)),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_time_entries_tenant_user_date", "time_entries", ["tenant_id", "user_id", "date"]
    )
    op.create_index(
        "ix_time_entries_tenant_project_date", "time_entries", ["tenant_id", "project_id", "date"]
    )
    op.create_index("ix_time_entries_tenant_status", "time_entries", ["tenant_id", "status"])

    op.create_table(
        "time_entry_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("time_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["time_entry_id"], ["time_entries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_approvals_time_entry", "time_entry_approvals", ["time_entry_id"])


def downgrade() -> None:
    op.drop_table("time_entry_approvals")
    op.drop_table("time_entries")

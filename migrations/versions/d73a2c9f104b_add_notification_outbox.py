
"""add notification outbox

Revision ID: d73a2c9f104b
Revises: c44f43df0a4f
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d73a2c9f104b"
down_revision: str | Sequence[str] | None = "c44f43df0a4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer(),
            sa.ForeignKey("incidents.id"),
            nullable=False,
        ),
        sa.Column(
            "channel",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'email'"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "recipient",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "subject",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "locked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "incident_id",
            "channel",
            name="uq_notification_outbox_incident_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed')",
            name="ck_notification_outbox_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_notification_outbox_attempts",
        ),
    )

    op.create_index(
        "ix_notification_outbox_queue",
        "notification_outbox",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_outbox_queue",
        table_name="notification_outbox",
    )
    op.drop_table("notification_outbox")

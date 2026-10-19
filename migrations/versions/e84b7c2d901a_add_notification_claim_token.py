
"""Add claim token to notification outbox.

Revision ID: e84b7c2d901a
Revises: d73a2c9f104b
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e84b7c2d901a"
down_revision: str | Sequence[str] | None = "d73a2c9f104b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_outbox",
        sa.Column(
            "claim_token",
            sa.Uuid(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "notification_outbox",
        "claim_token",
    )

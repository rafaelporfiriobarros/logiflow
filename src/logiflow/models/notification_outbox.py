
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from logiflow.db.base import Base


class NotificationOutbox(Base):
    
    
    claim_token: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    __tablename__ = "notification_outbox"

    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "channel",
            name="uq_notification_outbox_incident_channel",
        ),
        CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed')",
            name="ck_notification_outbox_status",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="ck_notification_outbox_attempts",
        ),
        Index(
            "ix_notification_outbox_queue",
            "status",
            "next_attempt_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    incident_id: Mapped[int] = mapped_column(
        ForeignKey("incidents.id"),
        nullable=False,
    )

    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="email",
        server_default=text("'email'"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )

    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    last_error: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

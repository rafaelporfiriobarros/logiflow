
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from logiflow.models.notification_outbox import NotificationOutbox

MAX_ATTEMPTS = 3
LEASE_MINUTES = 10
MAX_BATCH_SIZE = 50


def claim_notifications(
    db,
    limit: int = 10,
    now=None,
    notification_id: int | None = None,
):
    """
    Reserva notificações para processamento.

    Não executa commit. O chamador é responsável
    por confirmar ou reverter a transação.
    """

    if not 1 <= limit <= MAX_BATCH_SIZE:
        raise ValueError(
            f"limit deve estar entre 1 e {MAX_BATCH_SIZE}"
        )

    reference_time = now or datetime.now(UTC)

    if reference_time.tzinfo is None:
        raise ValueError("now deve conter timezone")

    lease_expiration = reference_time - timedelta(
        minutes=LEASE_MINUTES
    )

    eligible = or_(
        and_(
            NotificationOutbox.status.in_(["pending", "failed"]),
            NotificationOutbox.next_attempt_at <= reference_time,
        ),
        and_(
            NotificationOutbox.status == "sending",
            NotificationOutbox.locked_at <= lease_expiration,
        ),
    )

    statement = (
        select(NotificationOutbox)
        .where(
            eligible,
            NotificationOutbox.attempts < MAX_ATTEMPTS,
        )
        .order_by(
            NotificationOutbox.next_attempt_at,
            NotificationOutbox.id,
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )

    if notification_id is not None:
        statement = statement.where(NotificationOutbox.id == notification_id)

    notifications = list(db.scalars(statement).all())

    for notification in notifications:
        notification.status = "sending"
        notification.claim_token = uuid4()
        notification.locked_at = reference_time
        notification.attempts += 1
        notification.last_error = None

    db.flush()

    return notifications



class InvalidNotificationClaimError(Exception):
    """Reserva inexistente, expirada ou inválida."""


def mark_notification_sent(
    db: Session,
    notification_id: int,
    claim_token: UUID,
    now: datetime | None = None,
) -> None:
    reference_time = now or datetime.now(UTC)

    if reference_time.tzinfo is None:
        raise ValueError("now deve conter timezone")

    statement = (
        update(NotificationOutbox)
        .where(
            NotificationOutbox.id == notification_id,
            NotificationOutbox.status == "sending",
            NotificationOutbox.claim_token == claim_token,
            NotificationOutbox.locked_at
            > reference_time - timedelta(minutes=LEASE_MINUTES),
        )
        .values(
            status="sent",
            sent_at=reference_time,
            claim_token=None,
            locked_at=None,
            last_error=None,
            updated_at=reference_time,
        )
    )

    result = db.execute(statement)

    if result.rowcount != 1:
        raise InvalidNotificationClaimError(
            "Reserva inválida ou expirada."
        )


def mark_notification_failed(
    db: Session,
    notification_id: int,
    claim_token: UUID,
    error_message: str,
    now: datetime | None = None,
) -> None:
    reference_time = now or datetime.now(UTC)

    if reference_time.tzinfo is None:
        raise ValueError("now deve conter timezone")

    notification = db.scalar(
        select(NotificationOutbox)
        .where(
            NotificationOutbox.id == notification_id,
            NotificationOutbox.status == "sending",
            NotificationOutbox.claim_token == claim_token,
            NotificationOutbox.locked_at
            > reference_time - timedelta(minutes=LEASE_MINUTES),
        )
        .with_for_update()
    )

    if notification is None:
        raise InvalidNotificationClaimError(
            "Reserva inválida ou expirada."
        )

    retry_minutes = min(
        5 * (2 ** (notification.attempts - 1)),
        60,
    )

    notification.status = "failed"
    notification.claim_token = None
    notification.locked_at = None
    notification.last_error = error_message[:1000]
    notification.next_attempt_at = (
        reference_time + timedelta(minutes=retry_minutes)
    )
    notification.updated_at = reference_time

    db.flush()

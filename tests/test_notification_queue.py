
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services.notification_queue import (
    MAX_ATTEMPTS,
    InvalidNotificationClaimError,
    claim_notifications,
    mark_notification_failed,
    mark_notification_sent,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def create_notification(db, status="pending", attempts=0):
    customer = Customer(
        name="Cliente Queue",
        email=f"cliente-{uuid4().hex}@example.com",
    )
    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number=f"ORD-{customer.id}",
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code=f"TRK-{customer.id}",
        status="in_transit",
        expected_delivery_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(shipment)
    db.flush()

    incident = Incident(
        shipment_id=shipment.id,
        incident_type="delivery_delay",
        severity="high",
        status="open",
    )
    db.add(incident)
    db.flush()

    notification = NotificationOutbox(
        incident_id=incident.id,
        recipient="operacoes@example.com",
        subject="Alerta de atraso",
        body="Remessa atrasada",
        status=status,
        attempts=attempts,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def test_claim_pending_notification(db):
    notification = create_notification(db)

    claimed = claim_notifications(db)

    assert len(claimed) == 1
    assert claimed[0].id == notification.id
    assert claimed[0].status == "sending"
    assert claimed[0].claim_token is not None
    assert claimed[0].locked_at is not None
    assert claimed[0].attempts == 1


def test_does_not_claim_twice(db):
    create_notification(db)

    first = claim_notifications(db)
    db.commit()

    second = claim_notifications(db)

    assert len(first) == 1
    assert second == []


def test_expired_claim_gets_new_token(db):
    notification = create_notification(
        db,
        status="sending",
        attempts=1,
    )

    old_token = notification.claim_token
    notification.locked_at = (
        datetime.now(UTC) - timedelta(minutes=20)
    )
    db.commit()

    claimed = claim_notifications(db)

    assert len(claimed) == 1
    assert claimed[0].claim_token != old_token
    assert claimed[0].attempts == 2


def test_max_attempts_not_claimed(db):
    create_notification(
        db,
        status="failed",
        attempts=MAX_ATTEMPTS,
    )

    claimed = claim_notifications(db)

    assert claimed == []


def test_rejects_invalid_limit(db):
    with pytest.raises(ValueError):
        claim_notifications(db, limit=0)

    with pytest.raises(ValueError):
        claim_notifications(db, limit=51)


def test_failed_notification_waits_until_due(db):
    notification = create_notification(
        db,
        status="failed",
        attempts=1,
    )

    notification.next_attempt_at = (
        datetime.now(UTC) + timedelta(hours=1)
    )
    db.commit()

    claimed = claim_notifications(db)

    assert claimed == []
    

def test_mark_notification_sent(db):
    notification = create_notification(db)
    claimed = claim_notifications(db)
    token = claimed[0].claim_token

    mark_notification_sent(
        db,
        notification_id=notification.id,
        claim_token=token,
    )
    db.commit()
    db.refresh(notification)

    assert notification.status == "sent"
    assert notification.sent_at is not None
    assert notification.claim_token is None
    assert notification.locked_at is None


def test_mark_notification_sent_invalid_token(db):
    notification = create_notification(db)
    claim_notifications(db)

    with pytest.raises(InvalidNotificationClaimError):
        mark_notification_sent(
            db,
            notification_id=notification.id,
            claim_token=uuid4(),
        )


def test_mark_notification_failed_schedules_retry(db):
    notification = create_notification(db)
    claimed = claim_notifications(db)
    token = claimed[0].claim_token

    reference_time = datetime.now(UTC)

    mark_notification_failed(
        db,
        notification_id=notification.id,
        claim_token=token,
        error_message="SMTP temporariamente indisponível",
        now=reference_time,
    )

    db.commit()
    db.refresh(notification)

    assert notification.status == "failed"
    assert notification.claim_token is None
    assert notification.locked_at is None
    assert notification.attempts == 1
    assert notification.last_error == (
        "SMTP temporariamente indisponível"
    )
    assert notification.next_attempt_at.replace(
        tzinfo=UTC
    ) == reference_time + timedelta(minutes=5)


def test_mark_notification_failed_invalid_token(db):
    notification = create_notification(db)
    claim_notifications(db)

    with pytest.raises(InvalidNotificationClaimError):
        mark_notification_failed(
            db,
            notification_id=notification.id,
            claim_token=uuid4(),
            error_message="Falha simulada",
        )


def test_expired_claim_cannot_be_confirmed(db):
    notification = create_notification(db)
    claimed = claim_notifications(db)
    token = claimed[0].claim_token

    future_time = datetime.now(UTC) + timedelta(minutes=20)

    with pytest.raises(InvalidNotificationClaimError):
        mark_notification_sent(
            db,
            notification_id=notification.id,
            claim_token=token,
            now=future_time,
        )


def test_failed_notification_reaches_max_attempts(db):
    notification = create_notification(
        db,
        status="failed",
        attempts=MAX_ATTEMPTS - 1,
    )

    reference_time = datetime.now(UTC)

    claimed = claim_notifications(
        db,
        now=reference_time,
    )

    assert len(claimed) == 1
    assert claimed[0].attempts == MAX_ATTEMPTS

    mark_notification_failed(
        db,
        notification_id=notification.id,
        claim_token=claimed[0].claim_token,
        error_message="Falha definitiva simulada",
        now=reference_time,
    )

    db.commit()

    next_claim = claim_notifications(
        db,
        now=reference_time + timedelta(hours=2),
    )

    assert next_claim == []



def test_targeted_claim_service_preserves_other_pending(db):
    first = create_notification(db)
    second = create_notification(db)
    claimed = claim_notifications(db, limit=1, notification_id=second.id)
    assert [item.id for item in claimed] == [second.id]
    db.refresh(first)
    assert first.status == "pending"


from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment


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


def create_incident(db: Session) -> Incident:
    customer = Customer(
        name="Cliente Outbox",
        email="cliente@example.com",
    )
    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number="ORD-OUTBOX-001",
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code="TRK-OUTBOX-001",
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

    return incident


def test_notification_defaults(db):
    incident = create_incident(db)

    notification = NotificationOutbox(
        incident_id=incident.id,
        recipient="operacoes@example.com",
        subject="Novo atraso",
        body="Uma entrega está atrasada.",
    )

    db.add(notification)
    db.commit()

    saved = db.scalar(select(NotificationOutbox))

    assert saved is not None
    assert saved.status == "pending"
    assert saved.channel == "email"
    assert saved.attempts == 0
    assert saved.created_at is not None
    assert saved.next_attempt_at is not None


def test_does_not_allow_duplicate_incident_channel(db):
    incident = create_incident(db)

    first = NotificationOutbox(
        incident_id=incident.id,
        channel="email",
        recipient="operacoes@example.com",
        subject="Alerta 1",
        body="Mensagem 1",
    )

    db.add(first)
    db.commit()

    duplicate = NotificationOutbox(
        incident_id=incident.id,
        channel="email",
        recipient="operacoes@example.com",
        subject="Alerta 2",
        body="Mensagem 2",
    )

    db.add(duplicate)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_notification_status_constraint(db):
    incident = create_incident(db)

    notification = NotificationOutbox(
        incident_id=incident.id,
        status="invalid",
        recipient="operacoes@example.com",
        subject="Teste",
        body="Teste",
    )

    db.add(notification)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_notification_references_existing_incident(db):
    incident = create_incident(db)

    notification = NotificationOutbox(
        incident_id=incident.id,
        recipient="operacoes@example.com",
        subject="Novo incidente",
        body="Entrega atrasada",
    )

    db.add(notification)
    db.commit()

    assert notification.incident_id == incident.id

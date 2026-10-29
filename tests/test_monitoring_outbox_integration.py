
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import logiflow.models  # noqa: F401
from logiflow.db.base import Base
from logiflow.models.customer import Customer
from logiflow.models.incident import Incident
from logiflow.models.notification_outbox import NotificationOutbox
from logiflow.models.order import Order
from logiflow.models.shipment import Shipment
from logiflow.services.delay_monitor import detect_delivery_delays
from logiflow.services.notification_service import (
    enqueue_incident_notifications,
)


@pytest.fixture
def test_db():
    url = os.getenv("TEST_DATABASE_URL")

    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada.")

    if urlsplit(url).path.lstrip("/") != "logiflow_test":
        pytest.fail(
            "Teste bloqueado: utilize exclusivamente logiflow_test."
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("Este teste exige PostgreSQL.")

    Base.metadata.create_all(engine)

    connection = engine.connect()
    transaction = connection.begin()

    db = Session(bind=connection, expire_on_commit=False)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def create_shipment(db, *, delayed=True, delivered=False):
    unique_id = uuid4().hex[:12]

    customer = Customer(
        name="Cliente Teste Outbox",
        email=f"outbox-{unique_id}@example.com",
    )
    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number=f"ORD-OUT-{unique_id}",
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code=f"TRK-OUT-{unique_id}",
        status="delivered" if delivered else "in_transit",
        expected_delivery_at=(
            datetime.now(UTC) - timedelta(days=1)
            if delayed
            else datetime.now(UTC) + timedelta(days=1)
        ),
        delivered_at=datetime.now(UTC) if delivered else None,
    )

    db.add(shipment)
    db.flush()

    return shipment


def test_delayed_shipment_creates_incident_and_notification(test_db):
    db = test_db
    shipment = create_shipment(db)

    result = detect_delivery_delays(db)

    assert shipment.id in {
        incident.shipment_id
        for incident in db.scalars(
            select(Incident).where(
                Incident.id.in_(result.created_incident_ids)
            )
        )
    }

    assert shipment.id is not None
    assert result.created_incidents >= 1

    created = enqueue_incident_notifications(
        db=db,
        incident_ids=result.created_incident_ids,
        recipient="operacoes@example.com",
    )

    assert created == len(result.created_incident_ids)

    notification = db.scalar(
        select(NotificationOutbox)
        .join(Incident, Incident.id == NotificationOutbox.incident_id)
        .where(Incident.shipment_id == shipment.id)
    )

    assert notification is not None
    assert notification.status == "pending"
    assert notification.channel == "email"
    assert notification.recipient == "operacoes@example.com"
    assert shipment.tracking_code in notification.subject


def test_repeated_monitoring_does_not_duplicate_notifications(test_db):
    db = test_db
    shipment = create_shipment(db)

    first = detect_delivery_delays(db)

    enqueue_incident_notifications(
        db=db,
        incident_ids=first.created_incident_ids,
        recipient="operacoes@example.com",
    )

    second = detect_delivery_delays(db)

    assert second.created_incidents == 0
    assert second.created_incident_ids == []

    count = db.scalar(
        select(func.count())
        .select_from(NotificationOutbox)
        .join(Incident, Incident.id == NotificationOutbox.incident_id)
        .where(Incident.shipment_id == shipment.id)
    )

    assert count == 1


def test_delivered_shipment_does_not_create_incident(test_db):
    db = test_db
    shipment = create_shipment(db, delivered=True)

    result = detect_delivery_delays(db)

    assert shipment.id not in {
        incident.shipment_id
        for incident in db.scalars(
            select(Incident).where(
                Incident.id.in_(result.created_incident_ids)
            )
        )
    }

    count = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.shipment_id == shipment.id)
    )

    assert count == 0


def test_enqueue_failure_rolls_back_incident_and_notification(test_db):
    db = test_db
    shipment = create_shipment(db)

    # SAVEPOINT permite simular o rollback da unidade de trabalho
    # sem perder os dados sintéticos de preparação.
    with pytest.raises(ValueError, match="Destinatário"), db.begin_nested():
        result = detect_delivery_delays(db)

        enqueue_incident_notifications(
            db=db,
            incident_ids=result.created_incident_ids,
            recipient="",
        )

    incident_count = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.shipment_id == shipment.id)
    )

    notification_count = db.scalar(
        select(func.count())
        .select_from(NotificationOutbox)
        .join(Incident, Incident.id == NotificationOutbox.incident_id)
        .where(Incident.shipment_id == shipment.id)
    )

    assert incident_count == 0
    assert notification_count == 0

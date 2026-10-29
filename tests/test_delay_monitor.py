from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import logiflow.models  # noqa: F401
from logiflow.db.base import Base
from logiflow.models.customer import Customer
from logiflow.models.incident import Incident
from logiflow.models.order import Order
from logiflow.models.shipment import Shipment
from logiflow.services.delay_monitor import detect_delivery_delays


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


def create_shipment(
    db: Session,
    tracking_code: str,
    deadline: datetime,
    status: str = "in_transit",
) -> Shipment:
    customer = Customer(
        name=f"Cliente {tracking_code}",
        email=f"{tracking_code.lower()}@example.com",
    )
    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number=f"ORD-{tracking_code}",
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code=tracking_code,
        status=status,
        expected_delivery_at=deadline,
        delivered_at=deadline if status == "delivered" else None,
    )

    db.add(shipment)
    db.flush()

    return shipment


def test_creates_incident_for_delayed_shipment(db):
    now = datetime.now(UTC)

    create_shipment(
        db,
        "TRK-001",
        now - timedelta(days=2),
    )

    result = detect_delivery_delays(db, now=now)

    assert result.delayed_shipments == 1
    assert result.created_incidents == 1

    incident = db.scalar(select(Incident))

    assert incident is not None
    assert incident.incident_type == "delivery_delay"
    assert incident.severity == "high"
    assert incident.status == "open"


def test_does_not_duplicate_open_incident(db):
    now = datetime.now(UTC)

    create_shipment(
        db,
        "TRK-002",
        now - timedelta(days=1),
    )

    first = detect_delivery_delays(db, now=now)
    second = detect_delivery_delays(db, now=now)

    assert first.created_incidents == 1
    assert second.created_incidents == 0
    assert second.existing_incidents == 1

    total = db.scalar(select(func.count()).select_from(Incident))

    assert total == 1


def test_ignores_shipments_with_future_deadline(db):
    now = datetime.now(UTC)

    create_shipment(
        db,
        "TRK-003",
        now + timedelta(days=3),
    )

    result = detect_delivery_delays(db, now=now)

    assert result.delayed_shipments == 0
    assert result.created_incidents == 0


def test_ignores_delivered_shipments(db):
    now = datetime.now(UTC)

    create_shipment(
        db,
        "TRK-004",
        now - timedelta(days=2),
        status="delivered",
    )

    result = detect_delivery_delays(db, now=now)

    assert result.delayed_shipments == 0
    assert result.created_incidents == 0


def test_reopens_incident_after_previous_resolution(db):
    now = datetime.now(UTC)

    shipment = create_shipment(
        db,
        "TRK-005",
        now - timedelta(days=2),
    )

    db.add(
        Incident(
            shipment_id=shipment.id,
            incident_type="delivery_delay",
            severity="high",
            status="resolved",
        )
    )
    db.flush()

    result = detect_delivery_delays(db, now=now)

    assert result.created_incidents == 1

    total = db.scalar(select(func.count()).select_from(Incident))

    assert total == 2

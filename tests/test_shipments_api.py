from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import logiflow.models  # noqa: F401
from logiflow.db.base import Base
from logiflow.db.session import get_db
from logiflow.main import app
from logiflow.models.customer import Customer
from logiflow.models.order import Order
from logiflow.models.shipment import Shipment


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with testing_session() as db:
        customer = Customer(
            name="Cliente Teste",
            email="cliente@example.com",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            order_number="ORD-001",
            status="created",
        )
        db.add(order)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_code="LOG-001",
            status="pending",
            expected_delivery_at=datetime.now(UTC),
        )
        db.add(shipment)
        db.commit()

        shipment_id = shipment.id

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client, shipment_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_get_shipment(client):
    api, shipment_id = client

    response = api.get(f"/api/v1/shipments/{shipment_id}")

    assert response.status_code == 200
    assert response.json()["tracking_code"] == "LOG-001"
    assert response.json()["status"] == "pending"


def test_update_shipment_status(client):
    api, shipment_id = client

    response = api.patch(
        f"/api/v1/shipments/{shipment_id}/status",
        json={
            "status": "collected",
            "description": "Mercadoria coletada.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "collected"

    events = api.get(f"/api/v1/shipments/{shipment_id}/events")

    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["event_type"] == "collected"


def test_invalid_status_transition(client):
    api, shipment_id = client

    response = api.patch(
        f"/api/v1/shipments/{shipment_id}/status",
        json={"status": "delivered"},
    )

    assert response.status_code == 409

    events = api.get(f"/api/v1/shipments/{shipment_id}/events")
    assert events.json() == []


def test_shipment_not_found(client):
    api, _ = client

    response = api.get("/api/v1/shipments/999999")

    assert response.status_code == 404


def test_status_update_not_found(client):
    api, _ = client

    response = api.patch(
        "/api/v1/shipments/999999/status",
        json={"status": "collected"},
    )

    assert response.status_code == 404

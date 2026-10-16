from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from logiflow_ai.db.base import Base
from logiflow_ai.db.session import get_db
from logiflow_ai.main import app
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def incident(db):
    customer = Customer(
        name="Cliente teste incidentes",
        email="incident-test@example.com",
    )
    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number="INC-ORDER-001",
    )
    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code="INC-TRK-001",
        status="in_transit",
        expected_delivery_at=(datetime.now(UTC) - timedelta(days=1)),
    )
    db.add(shipment)
    db.flush()

    item = Incident(
        shipment_id=shipment.id,
        incident_type="delivery_delay",
        severity="high",
        status="open",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def test_list_incidents(client, incident):
    response = client.get("/api/v1/incidents")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == incident.id


def test_filter_incidents_by_status(client, incident):
    response = client.get(
        "/api/v1/incidents",
        params={"status": "open"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get(
        "/api/v1/incidents",
        params={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_incident(client, incident):
    response = client.get(f"/api/v1/incidents/{incident.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_incident_not_found(client):
    response = client.get("/api/v1/incidents/99999")

    assert response.status_code == 404


def test_resolve_incident(client, incident, db):
    response = client.patch(f"/api/v1/incidents/{incident.id}/resolve")

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"

    db.refresh(incident)
    assert incident.status == "resolved"


def test_cannot_resolve_twice(client, incident):
    first = client.patch(f"/api/v1/incidents/{incident.id}/resolve")

    second = client.patch(f"/api/v1/incidents/{incident.id}/resolve")

    assert first.status_code == 200
    assert second.status_code == 409


def test_invalid_status_filter(client):
    response = client.get(
        "/api/v1/incidents",
        params={"status": "invalid"},
    )

    assert response.status_code == 422

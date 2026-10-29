from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from logiflow.db.base import Base
from logiflow.db.session import get_db
from logiflow.main import app
from logiflow.models.customer import Customer
from logiflow.models.order import Order
from logiflow.models.shipment import Shipment


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv(
        "MONITORING_API_KEY",
        "test-monitoring-key",
    )

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
def authorized_client(client):
    client.headers.update({"X-API-Key": "test-monitoring-key"})

    return client


@pytest.fixture
def delayed_shipment(db):
    customer = Customer(
        name="Cliente monitoramento",
        email="monitoring-test@example.com",
    )

    db.add(customer)
    db.flush()

    order = Order(
        customer_id=customer.id,
        order_number="MON-ORDER-001",
    )

    db.add(order)
    db.flush()

    shipment = Shipment(
        order_id=order.id,
        tracking_code="MON-TRK-001",
        status="in_transit",
        expected_delivery_at=(datetime.now(UTC) - timedelta(days=1)),
    )

    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    return shipment


def test_monitoring_requires_api_key(client):
    response = client.get("/api/v1/monitoring/runs")

    assert response.status_code == 401


def test_monitoring_rejects_invalid_key(client):
    response = client.get(
        "/api/v1/monitoring/runs",
        headers={"X-API-Key": "wrong-key"},
    )

    assert response.status_code == 401


def test_monitoring_lists_empty_runs(authorized_client):
    response = authorized_client.get("/api/v1/monitoring/runs")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_monitoring_run_not_found(authorized_client):
    response = authorized_client.get("/api/v1/monitoring/runs/99999")

    assert response.status_code == 404


def test_monitoring_creates_run(
    authorized_client,
    delayed_shipment,
):
    response = authorized_client.post("/api/v1/monitoring/delays")

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "success"
    assert data["delayed_shipments"] == 1
    assert data["created_incidents"] == 1
    assert data["existing_incidents"] == 0


def test_monitoring_is_idempotent(
    authorized_client,
    delayed_shipment,
):
    first = authorized_client.post("/api/v1/monitoring/delays")

    second = authorized_client.post("/api/v1/monitoring/delays")

    assert first.status_code == 201
    assert second.status_code == 201

    assert first.json()["created_incidents"] == 1
    assert second.json()["created_incidents"] == 0
    assert second.json()["existing_incidents"] == 1


def test_monitoring_run_can_be_retrieved(
    authorized_client,
    delayed_shipment,
):
    execution = authorized_client.post("/api/v1/monitoring/delays")

    run_id = execution.json()["id"]

    response = authorized_client.get(f"/api/v1/monitoring/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["id"] == run_id


def test_monitoring_validates_pagination(authorized_client):
    response = authorized_client.get(
        "/api/v1/monitoring/runs",
        params={"limit": 0},
    )

    assert response.status_code == 422

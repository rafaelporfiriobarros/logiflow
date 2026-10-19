
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import logiflow_ai.api.dependencies.api_key as api_key_module
import logiflow_ai.models  # noqa: F401
from logiflow_ai.core.config import get_settings
from logiflow_ai.db.base import Base
from logiflow_ai.db.session import get_db
from logiflow_ai.main import app
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment

API_KEY = "logiflow-test-api-key"
HEADERS = {"X-API-Key": API_KEY}
BASE_URL = "/api/v1/notifications"


@pytest.fixture
def api_context(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    monkeypatch.setattr(
        api_key_module,
        "get_expected_api_key",
        lambda: API_KEY,
    )

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def create_notification(engine):
    with Session(engine) as db:
        customer = Customer(
            name="Cliente API",
            email=f"cliente-api-{uuid4().hex}@example.com",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            order_number=f"ORD-API-{customer.id}",
        )
        db.add(order)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_code=f"TRK-API-{customer.id}",
            status="in_transit",
            expected_delivery_at=(
                datetime.now(UTC) - timedelta(days=1)
            ),
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
            status="pending",
            attempts=0,
        )
        db.add(notification)
        db.commit()

        return notification.id


def test_claim_requires_api_key(api_context):
    client, _ = api_context

    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
    )

    assert response.status_code == 401


def test_claim_rejects_invalid_api_key(api_context):
    client, _ = api_context

    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers={"X-API-Key": "invalid-key"},
    )

    assert response.status_code == 401


def test_claim_returns_empty_queue(api_context):
    client, _ = api_context

    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
    }


def test_claim_reserves_notification(api_context):
    client, engine = api_context
    notification_id = create_notification(engine)

    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["id"] == notification_id
    assert item["recipient"] == "operacoes@example.com"
    assert item["attempts"] == 1
    assert item["claim_token"]

    with Session(engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "sending"
        assert notification.claim_token is not None
        assert notification.attempts == 1


def test_claim_does_not_reserve_twice(api_context):
    client, engine = api_context
    create_notification(engine)

    first = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    second = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    assert first.status_code == 200
    assert first.json()["total"] == 1

    assert second.status_code == 200
    assert second.json()["total"] == 0


def test_claim_rejects_invalid_limit(api_context):
    client, _ = api_context

    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 51},
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_confirm_sent(api_context):
    client, engine = api_context
    notification_id = create_notification(engine)

    claim_response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    token = claim_response.json()["items"][0]["claim_token"]

    response = client.post(
        f"{BASE_URL}/{notification_id}/sent",
        json={"claim_token": token},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert response.json()["sent_at"] is not None

    with Session(engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "sent"
        assert notification.claim_token is None


def test_confirm_sent_rejects_invalid_token(api_context):
    client, engine = api_context
    notification_id = create_notification(engine)

    client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    response = client.post(
        f"{BASE_URL}/{notification_id}/sent",
        json={"claim_token": str(uuid4())},
        headers=HEADERS,
    )

    assert response.status_code == 409

    with Session(engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "sending"


def test_confirm_failed_schedules_retry(api_context):
    client, engine = api_context
    notification_id = create_notification(engine)

    claim_response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    token = claim_response.json()["items"][0]["claim_token"]

    response = client.post(
        f"{BASE_URL}/{notification_id}/failed",
        json={
            "claim_token": token,
            "error_message": "SMTP indisponível",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["attempts"] == 1

    with Session(engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "failed"
        assert notification.last_error == "SMTP indisponível"
        assert notification.claim_token is None
        assert notification.next_attempt_at is not None


def test_confirm_failed_rejects_empty_error(api_context):
    client, engine = api_context
    notification_id = create_notification(engine)

    claim_response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 10},
        headers=HEADERS,
    )

    token = claim_response.json()["items"][0]["claim_token"]

    response = client.post(
        f"{BASE_URL}/{notification_id}/failed",
        json={
            "claim_token": token,
            "error_message": "",
        },
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_targeted_claim_only_selects_requested_id(api_context, monkeypatch):
    client, engine = api_context
    first_id = create_notification(engine)
    second_id = create_notification(engine)
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        response = client.post(
            f"{BASE_URL}/claim",
            json={"limit": 1, "notification_id": second_id},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert [x["id"] for x in response.json()["items"]] == [second_id]
        with Session(engine) as db:
            assert db.get(NotificationOutbox, first_id).status == "pending"
    finally:
        get_settings.cache_clear()


def test_targeted_claim_nonexistent_returns_empty(api_context, monkeypatch):
    client, _ = api_context
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        response = client.post(
            f"{BASE_URL}/claim",
            json={"limit": 1, "notification_id": 999999},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0}
    finally:
        get_settings.cache_clear()


def test_targeted_claim_rejects_zero_id(api_context):
    client, _ = api_context
    response = client.post(
        f"{BASE_URL}/claim",
        json={"limit": 1, "notification_id": 0},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_targeted_claim_forbidden_in_production(api_context, monkeypatch):
    client, engine = api_context
    notification_id = create_notification(engine)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        response = client.post(
            f"{BASE_URL}/claim",
            json={"limit": 1, "notification_id": notification_id},
            headers=HEADERS,
        )
        assert response.status_code == 403
        with Session(engine) as db:
            assert db.get(NotificationOutbox, notification_id).status == "pending"
    finally:
        get_settings.cache_clear()


def test_targeted_claim_ineligible_returns_empty(api_context, monkeypatch):
    client, engine = api_context
    notification_id = create_notification(engine)
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        first = client.post(
            f"{BASE_URL}/claim",
            json={"limit": 1, "notification_id": notification_id},
            headers=HEADERS,
        )
        second = client.post(
            f"{BASE_URL}/claim",
            json={"limit": 1, "notification_id": notification_id},
            headers=HEADERS,
        )
        assert first.status_code == 200
        assert first.json()["total"] == 1
        assert second.status_code == 200
        assert second.json()["total"] == 0
    finally:
        get_settings.cache_clear()

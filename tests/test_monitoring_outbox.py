
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.monitoring_run import MonitoringRun
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services.monitoring_service import execute_delay_monitoring


@pytest.fixture
def session_factory(monkeypatch):
    from logiflow_ai.core.config import get_settings

    monkeypatch.setenv(
        "ALERTS_EMAIL_TO",
        "operacoes@example.com",
    )

    # Limpa configurações armazenadas anteriormente
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    try:
        yield factory
    finally:
        # Libera recursos e limpa o cache após o teste
        engine.dispose()
        get_settings.cache_clear()



def seed_delayed_shipment(session_factory):
    with session_factory() as db:
        customer = Customer(
            name="Cliente Integração",
            email="integracao@example.com",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            order_number="ORD-OUTBOX-INTEGRATION",
        )
        db.add(order)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_code="TRK-OUTBOX-INTEGRATION",
            status="in_transit",
            expected_delivery_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.add(shipment)
        db.commit()


def count_records(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_new_incident_creates_pending_notification(session_factory):
    seed_delayed_shipment(session_factory)

    run = execute_delay_monitoring(session_factory)

    with session_factory() as db:
        incidents = db.scalars(select(Incident)).all()
        notifications = db.scalars(
            select(NotificationOutbox)
        ).all()

        assert run.status == "success"
        assert run.created_incidents == 1

        assert len(incidents) == 1
        assert len(notifications) == 1

        notification = notifications[0]

        assert notification.incident_id == incidents[0].id
        assert notification.status == "pending"
        assert notification.channel == "email"
        assert notification.attempts == 0
        assert notification.recipient == "operacoes@example.com"


def test_second_run_does_not_duplicate_notification(session_factory):
    seed_delayed_shipment(session_factory)

    first = execute_delay_monitoring(session_factory)
    second = execute_delay_monitoring(session_factory)

    with session_factory() as db:
        assert first.created_incidents == 1
        assert second.created_incidents == 0
        assert second.existing_incidents == 1

        assert count_records(db, Incident) == 1
        assert count_records(db, NotificationOutbox) == 1
        assert count_records(db, MonitoringRun) == 2


def test_notification_failure_rolls_back_incident(session_factory):
    seed_delayed_shipment(session_factory)

    with patch(
        "logiflow_ai.services.monitoring_service."
        "enqueue_incident_notifications",
        side_effect=RuntimeError("Falha simulada na outbox"),
    ), pytest.raises(
        RuntimeError,
        match="Falha simulada na outbox",
    ):
        execute_delay_monitoring(session_factory)

    with session_factory() as db:
        assert count_records(db, Incident) == 0
        assert count_records(db, NotificationOutbox) == 0

        runs = db.scalars(select(MonitoringRun)).all()

        assert len(runs) == 1
        assert runs[0].status == "failed"
        assert "Falha simulada na outbox" in runs[0].error_message

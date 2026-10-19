
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services.notification_queue import claim_notifications


@pytest.fixture
def postgres_engine():
    url = os.getenv("TEST_DATABASE_URL")

    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada")

    database_name = urlsplit(url).path.lstrip("/")

    if database_name != "logiflow_test":
        pytest.fail(
            "Teste bloqueado: use exclusivamente "
            "o banco logiflow_test."
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    if engine.dialect.name != "postgresql":
        engine.dispose()
        pytest.fail("Este teste exige PostgreSQL.")

    # Banco dedicado exclusivamente aos testes.
    Base.metadata.create_all(engine)

    try:
        yield engine
    finally:
        engine.dispose()


def seed_notification(engine):
    with Session(engine) as db:
        unique_id = uuid4().hex[:12]

        customer = Customer(
            name="Cliente Concorrência",
            email=f"concorrencia-{unique_id}@example.com",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            order_number=f"ORD-CONC-{unique_id}",
        )
        db.add(order)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_code=f"TRK-CONC-{unique_id}",
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
            subject="Teste de concorrência",
            body="Notificação de teste",
            status="pending",
            attempts=0,
        )
        db.add(notification)
        db.commit()

        return notification.id


def test_skip_locked_prevents_double_claim(postgres_engine):
    notification_id = seed_notification(postgres_engine)

    with (
        Session(postgres_engine) as worker_a,
        Session(postgres_engine) as worker_b,
    ):
        # Worker A reserva, mas ainda não confirma.
        claimed_a = claim_notifications(worker_a, limit=1, notification_id=notification_id)

        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id

        # Worker B usa outra conexão enquanto A mantém
        # o bloqueio da linha.
        claimed_b = claim_notifications(worker_b, limit=1, notification_id=notification_id)

        assert claimed_b == []

        # Confirma a reserva do primeiro worker.
        worker_a.commit()
        worker_b.commit()

    with Session(postgres_engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "sending"
        assert notification.attempts == 1
        assert notification.claim_token is not None


def test_rollback_releases_notification(postgres_engine):
    notification_id = seed_notification(postgres_engine)

    with Session(postgres_engine) as worker_a:
        claimed_a = claim_notifications(worker_a, limit=1, notification_id=notification_id)

        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id

        # Simula falha antes de confirmar a reserva.
        worker_a.rollback()

    with Session(postgres_engine) as worker_b:
        claimed_b = claim_notifications(worker_b, limit=1, notification_id=notification_id)

        assert len(claimed_b) == 1
        assert claimed_b[0].id == notification_id

        worker_b.commit()

    with Session(postgres_engine) as db:
        notification = db.get(
            NotificationOutbox,
            notification_id,
        )

        assert notification.status == "sending"
        assert notification.attempts == 1


def test_committed_claim_is_not_claimed_again(postgres_engine):
    notification_id = seed_notification(postgres_engine)

    with Session(postgres_engine) as worker_a:
        claimed_a = claim_notifications(worker_a, limit=1, notification_id=notification_id)
        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id
        worker_a.commit()

    with Session(postgres_engine) as worker_b:
        claimed_b = claim_notifications(worker_b, limit=1, notification_id=notification_id)

        assert claimed_b == []
        worker_b.rollback()

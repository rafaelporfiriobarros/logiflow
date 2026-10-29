
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import logiflow.models  # noqa: F401
from logiflow.models.customer import Customer
from logiflow.models.incident import Incident
from logiflow.models.notification_outbox import NotificationOutbox
from logiflow.models.order import Order
from logiflow.models.shipment import Shipment
from logiflow.services.notification_queue import claim_notifications


@pytest.fixture
def postgres_engine():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL não configurada.")

    url = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        pytest.fail("Este teste exige PostgreSQL.")

    if url.database != "logiflow_test":
        pytest.fail("Banco permitido: logiflow_test.")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    try:
        with engine.connect() as connection:
            database_name = connection.exec_driver_sql(
                "SELECT current_database()"
            ).scalar_one()

            if database_name != "logiflow_test":
                pytest.fail("Conexão fora do banco de testes.")

        yield engine

    finally:
        engine.dispose()


def seed_notification(engine):
    with Session(engine) as db:
        unique_id = uuid4().hex[:12]

        customer = Customer(
            name="Cliente Concorrência",
            email=f"concorrencia-{unique_id}@example.invalid",
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
            recipient="operacoes@example.invalid",
            subject="Teste de concorrência",
            body="Notificação sintética",
            status="pending",
            attempts=0,
        )
        db.add(notification)
        db.flush()

        notification_id = notification.id
        db.commit()

        return notification_id


def cleanup_notification(engine, notification_id: int) -> None:
    """Remove exclusivamente os registros criados pelo teste."""

    if notification_id == 1:
        raise RuntimeError("A notificação ID 1 está protegida.")

    with Session(engine) as db:
        notification = db.get(NotificationOutbox, notification_id)

        if notification is None:
            return

        incident = db.get(Incident, notification.incident_id)

        if incident is None:
            raise RuntimeError("Incidente associado não encontrado.")

        shipment = db.get(Shipment, incident.shipment_id)

        if shipment is None:
            raise RuntimeError("Remessa associada não encontrada.")

        order = db.get(Order, shipment.order_id)

        if order is None:
            raise RuntimeError("Pedido associado não encontrado.")

        if not order.order_number.startswith("ORD-CONC-"):
            raise RuntimeError(
                "Pedido fora do escopo dos testes de concorrência."
            )

        customer_id = order.customer_id
        order_id = order.id
        shipment_id = shipment.id
        incident_id = incident.id

        db.execute(
            delete(NotificationOutbox).where(
                NotificationOutbox.id == notification_id
            )
        )

        db.execute(
            delete(Incident).where(
                Incident.id == incident_id
            )
        )

        db.execute(
            delete(Shipment).where(
                Shipment.id == shipment_id
            )
        )

        db.execute(
            delete(Order).where(
                Order.id == order_id
            )
        )

        db.execute(
            delete(Customer).where(
                Customer.id == customer_id
            )
        )

        db.commit()


@pytest.fixture
def seeded_notification(postgres_engine):
    notification_id = seed_notification(postgres_engine)

    try:
        yield notification_id
    finally:
        cleanup_notification(postgres_engine, notification_id)


def test_skip_locked_prevents_double_claim(
    postgres_engine,
    seeded_notification,
):
    notification_id = seeded_notification

    with (
        Session(postgres_engine) as worker_a,
        Session(postgres_engine) as worker_b,
    ):
        claimed_a = claim_notifications(
            worker_a,
            limit=1,
            notification_id=notification_id,
        )

        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id

        claimed_b = claim_notifications(
            worker_b,
            limit=1,
            notification_id=notification_id,
        )

        assert claimed_b == []

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


def test_rollback_releases_notification(
    postgres_engine,
    seeded_notification,
):
    notification_id = seeded_notification

    with Session(postgres_engine) as worker_a:
        claimed_a = claim_notifications(
            worker_a,
            limit=1,
            notification_id=notification_id,
        )

        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id

        worker_a.rollback()

    with Session(postgres_engine) as worker_b:
        claimed_b = claim_notifications(
            worker_b,
            limit=1,
            notification_id=notification_id,
        )

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
        assert notification.claim_token is not None


def test_committed_claim_is_not_claimed_again(
    postgres_engine,
    seeded_notification,
):
    notification_id = seeded_notification

    with Session(postgres_engine) as worker_a:
        claimed_a = claim_notifications(
            worker_a,
            limit=1,
            notification_id=notification_id,
        )

        assert len(claimed_a) == 1
        assert claimed_a[0].id == notification_id

        worker_a.commit()

    with Session(postgres_engine) as worker_b:
        claimed_b = claim_notifications(
            worker_b,
            limit=1,
            notification_id=notification_id,
        )

        assert claimed_b == []
        worker_b.rollback()

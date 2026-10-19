
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.monitoring_run import MonitoringRun
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services import monitoring_service
from logiflow_ai.services.monitoring_service import (
    execute_delay_monitoring,
)


@pytest.fixture
def isolated_postgres(monkeypatch):
    """
    Cria um schema exclusivo para cada teste.

    Permite commits reais sem alterar as tabelas
    existentes no schema public.
    """
    url = os.getenv("TEST_DATABASE_URL")

    if not url:
        pytest.skip("TEST_DATABASE_URL não configurada.")

    if urlsplit(url).path.lstrip("/") != "logiflow_test":
        pytest.fail(
            "Teste bloqueado: use exclusivamente logiflow_test."
        )

    schema = f"test_monitor_{uuid4().hex[:16]}"

    admin_engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )

    test_engine = None
    schema_created = False

    try:
        if admin_engine.dialect.name != "postgresql":
            pytest.fail("Este teste exige PostgreSQL.")

        with admin_engine.begin() as connection:
            connection.execute(
                text(f'CREATE SCHEMA "{schema}"')
            )
            schema_created = True

        test_engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 5,
                "options": f"-csearch_path={schema}",
            },
        )

        Base.metadata.create_all(test_engine)

        factory = sessionmaker(
            bind=test_engine,
            expire_on_commit=False,
        )

        # Evita depender do destinatário real do .env.
        monkeypatch.setattr(
            monitoring_service,
            "get_settings",
            lambda: SimpleNamespace(
                alerts_email_to="operacoes@example.com"
            ),
        )

        yield factory

    finally:
        if test_engine is not None:
            test_engine.dispose()

        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(
                    text(f'DROP SCHEMA "{schema}" CASCADE')
                )

        admin_engine.dispose()


def create_delayed_shipment(factory):
    unique_id = uuid4().hex[:12]

    with factory() as db:
        customer = Customer(
            name="Cliente Monitoramento E2E",
            email=f"monitor-{unique_id}@example.com",
        )
        db.add(customer)
        db.flush()

        order = Order(
            customer_id=customer.id,
            order_number=f"ORD-MON-{unique_id}",
        )
        db.add(order)
        db.flush()

        shipment = Shipment(
            order_id=order.id,
            tracking_code=f"TRK-MON-{unique_id}",
            status="in_transit",
            expected_delivery_at=(
                datetime.now(UTC) - timedelta(days=1)
            ),
        )
        db.add(shipment)
        db.flush()

        shipment_id = shipment.id
        tracking_code = shipment.tracking_code

        db.commit()

    return shipment_id, tracking_code


def test_monitoring_creates_notification_and_is_idempotent(
    isolated_postgres,
):
    factory = isolated_postgres

    shipment_id, tracking_code = create_delayed_shipment(
        factory
    )

    # Primeira execução: cria incidente e notificação.
    first_run = execute_delay_monitoring(factory)

    assert first_run.status == "success"
    assert first_run.finished_at is not None
    assert first_run.delayed_shipments == 1
    assert first_run.created_incidents == 1
    assert first_run.existing_incidents == 0

    with factory() as db:
        incident = db.scalar(
            select(Incident).where(
                Incident.shipment_id == shipment_id
            )
        )

        assert incident is not None
        assert incident.incident_type == "delivery_delay"
        assert incident.status == "open"

        notification = db.scalar(
            select(NotificationOutbox).where(
                NotificationOutbox.incident_id == incident.id
            )
        )

        assert notification is not None
        assert notification.status == "pending"
        assert notification.channel == "email"
        assert notification.recipient == "operacoes@example.com"
        assert tracking_code in notification.subject
        assert notification.attempts == 0

    # Segunda execução: reconhece incidente existente.
    second_run = execute_delay_monitoring(factory)

    assert second_run.status == "success"
    assert second_run.delayed_shipments == 1
    assert second_run.created_incidents == 0
    assert second_run.existing_incidents == 1

    with factory() as db:
        incident_count = db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.shipment_id == shipment_id)
        )

        notification_count = db.scalar(
            select(func.count())
            .select_from(NotificationOutbox)
            .join(
                Incident,
                Incident.id == NotificationOutbox.incident_id,
            )
            .where(Incident.shipment_id == shipment_id)
        )

        run_count = db.scalar(
            select(func.count()).select_from(MonitoringRun)
        )

        assert incident_count == 1
        assert notification_count == 1
        assert run_count == 2


def test_monitoring_failure_rolls_back_incident(
    isolated_postgres,
    monkeypatch,
):
    factory = isolated_postgres

    shipment_id, _ = create_delayed_shipment(factory)

    def simulate_enqueue_failure(**kwargs):
        raise RuntimeError("Falha simulada na Outbox")

    monkeypatch.setattr(
        monitoring_service,
        "enqueue_incident_notifications",
        simulate_enqueue_failure,
    )

    with pytest.raises(
        RuntimeError,
        match="Falha simulada na Outbox",
    ):
        execute_delay_monitoring(factory)

    with factory() as db:
        incident_count = db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.shipment_id == shipment_id)
        )

        notification_count = db.scalar(
            select(func.count())
            .select_from(NotificationOutbox)
        )

        run = db.scalar(
            select(MonitoringRun)
            .order_by(MonitoringRun.id.desc())
        )

        # O incidente não pode ser confirmado
        # se o enfileiramento falhar.
        assert incident_count == 0
        assert notification_count == 0

        # A auditoria da falha permanece registrada.
        assert run is not None
        assert run.status == "failed"
        assert run.finished_at is not None
        assert "Falha simulada na Outbox" in run.error_message

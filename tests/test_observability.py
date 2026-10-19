
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import logiflow_ai.models  # noqa: F401
from logiflow_ai.db.base import Base
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.monitoring_run import MonitoringRun
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services.observability import get_observability_summary


def test_empty_database_returns_zero_metrics():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    try:
        with Session(engine) as db:
            summary = get_observability_summary(db)

        assert summary["incidents"]["total"] == 0
        assert summary["notifications"]["total"] == 0
        assert summary["notifications"]["success_rate_percent"] == 0
        assert summary["latest_monitoring_run"] is None
    finally:
        engine.dispose()


def test_observability_counts_notifications():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    try:
        with Session(engine) as db:
            customer = Customer(
                name="Cliente Observabilidade",
                email="observability@example.com",
            )
            db.add(customer)
            db.flush()

            order = Order(
                customer_id=customer.id,
                order_number="OBS-ORDER-001",
            )
            db.add(order)
            db.flush()

            shipment = Shipment(
                order_id=order.id,
                tracking_code="OBS-TRK-001",
                status="in_transit",
                expected_delivery_at=datetime.now(UTC),
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

            db.add(
                NotificationOutbox(
                    incident_id=incident.id,
                    recipient="operacoes@example.com",
                    subject="Alerta",
                    body="Remessa atrasada",
                    status="sent",
                    attempts=1,
                )
            )

            db.add(
                MonitoringRun(
                    status="success",
                    delayed_shipments=1,
                    created_incidents=1,
                    existing_incidents=0,
                )
            )

            db.commit()

            summary = get_observability_summary(db)

        assert summary["incidents"]["open"] == 1
        assert summary["notifications"]["total"] == 1
        assert summary["notifications"]["sent"] == 1
        assert summary["notifications"]["success_rate_percent"] == 100.0
        assert summary["notifications"]["attempts_by_status"]["sent"] == 1
        assert summary["latest_monitoring_run"]["status"] == "success"
    finally:
        engine.dispose()

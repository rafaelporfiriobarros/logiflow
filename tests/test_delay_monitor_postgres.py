from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from logiflow_ai.models.customer import Customer
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment
from logiflow_ai.services.delay_monitor import detect_delivery_delays


@pytest.mark.postgres
def test_concurrent_monitoring_creates_single_incident(
    postgres_test_session_factory,
):
    session_factory = postgres_test_session_factory

    identifier = uuid4().hex[:12]
    tracking_code = f"TEST-CONCURRENT-{identifier}"

    with session_factory() as db:
        customer = Customer(
            name="Cliente teste concorrência",
            email=f"test-{identifier}@example.com",
        )
        db.add(customer)
        db.flush()

        customer_id = customer.id

        order = Order(
            customer_id=customer_id,
            order_number=f"ORD-{identifier}",
        )
        db.add(order)
        db.flush()

        order_id = order.id

        shipment = Shipment(
            order_id=order_id,
            tracking_code=tracking_code,
            status="in_transit",
            expected_delivery_at=(datetime.now(UTC) - timedelta(days=1)),
        )
        db.add(shipment)
        db.flush()

        shipment_id = shipment.id

        db.commit()

    def run_monitor():
        with session_factory() as db:
            result = detect_delivery_delays(db)
            db.commit()
            return result

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run_monitor) for _ in range(2)]

            results = [future.result() for future in futures]

        with session_factory() as db:
            total = db.scalar(
                select(func.count())
                .select_from(Incident)
                .where(
                    Incident.shipment_id == shipment_id,
                    Incident.incident_type == "delivery_delay",
                    Incident.status == "open",
                )
            )

        assert total == 1
        assert sum(result.created_incidents for result in results) == 1

    finally:
        with session_factory() as db:
            db.query(Incident).filter(Incident.shipment_id == shipment_id).delete()

            db.query(Shipment).filter(Shipment.id == shipment_id).delete()

            db.query(Order).filter(Order.id == order_id).delete()

            db.query(Customer).filter(Customer.id == customer_id).delete()

            db.commit()

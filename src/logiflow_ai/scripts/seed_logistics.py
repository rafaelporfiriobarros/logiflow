from datetime import UTC, datetime, timedelta
from random import Random

from sqlalchemy import select

from logiflow_ai.db.session import SessionLocal
from logiflow_ai.models.customer import Customer
from logiflow_ai.models.delivery_event import DeliveryEvent
from logiflow_ai.models.incident import Incident
from logiflow_ai.models.order import Order
from logiflow_ai.models.shipment import Shipment

SEED_PREFIX = "DEMO-2026"
RNG = Random(42)

STATUS_PATHS = {
    "pending": [],
    "in_transit": ["collected", "in_transit"],
    "out_for_delivery": [
        "collected",
        "in_transit",
        "out_for_delivery",
    ],
    "delivered": [
        "collected",
        "in_transit",
        "out_for_delivery",
        "delivered",
    ],
    "delivery_failed": [
        "collected",
        "in_transit",
        "out_for_delivery",
        "delivery_failed",
    ],
}


def seed_logistics() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        existing = db.scalar(
            select(Customer.id).where(Customer.email == "cliente001@logiflow.example")
        )

        if existing is not None:
            print("Dados de demonstração já existem. Nenhuma alteração.")
            return

        try:
            customers = []

            for number in range(1, 21):
                customer = Customer(
                    name=f"Cliente Logístico {number:03d}",
                    email=f"cliente{number:03d}@logiflow.example",
                    phone=f"1199000{number:04d}",
                )
                customers.append(customer)

            db.add_all(customers)
            db.flush()

            statuses = list(STATUS_PATHS)

            for number in range(1, 101):
                customer = customers[(number - 1) % len(customers)]
                status = statuses[(number - 1) % len(statuses)]

                created_at = now - timedelta(days=RNG.randint(2, 15))
                deadline = created_at + timedelta(days=RNG.randint(2, 6))

                order = Order(
                    customer_id=customer.id,
                    order_number=f"{SEED_PREFIX}-ORD-{number:04d}",
                    status="created",
                    created_at=created_at,
                )

                db.add(order)
                db.flush()

                delivered_at = (
                    created_at + timedelta(days=2) if status == "delivered" else None
                )

                shipment = Shipment(
                    order_id=order.id,
                    tracking_code=f"{SEED_PREFIX}-TRK-{number:04d}",
                    status=status,
                    expected_delivery_at=deadline,
                    delivered_at=delivered_at,
                    created_at=created_at,
                )

                db.add(shipment)
                db.flush()

                for index, event_type in enumerate(STATUS_PATHS[status], start=1):
                    db.add(
                        DeliveryEvent(
                            shipment_id=shipment.id,
                            event_type=event_type,
                            description=f"Evento: {event_type}",
                            occurred_at=created_at + timedelta(hours=index * 8),
                        )
                    )

                if status == "delivery_failed":
                    db.add(
                        Incident(
                            shipment_id=shipment.id,
                            incident_type="delivery_attempt_failed",
                            severity="medium",
                            status="open",
                        )
                    )

                elif status not in {"delivered", "pending"} and deadline < now:
                    db.add(
                        Incident(
                            shipment_id=shipment.id,
                            incident_type="delivery_delay",
                            severity="high",
                            status="open",
                        )
                    )

            db.commit()

        except Exception:
            db.rollback()
            raise

    print("Dados sintéticos inseridos com sucesso.")
    print("Clientes: 20")
    print("Pedidos: 100")
    print("Remessas: 100")


if __name__ == "__main__":
    seed_logistics()

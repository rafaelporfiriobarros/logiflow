from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from logiflow_ai.models.incident import Incident
from logiflow_ai.models.shipment import Shipment


@dataclass(frozen=True)
class DelayMonitorResult:
    delayed_shipments: int
    created_incidents: int
    existing_incidents: int


def detect_delivery_delays(
    db: Session,
    now: datetime | None = None,
) -> DelayMonitorResult:
    """Detecta atrasos e cria incidentes sem duplicações."""

    reference_time = now or datetime.now(UTC)

    if reference_time.tzinfo is None:
        raise ValueError("O horário de referência deve conter timezone.")

    delayed_shipments = db.scalars(
        select(Shipment)
        .where(
            Shipment.expected_delivery_at < reference_time,
            Shipment.delivered_at.is_(None),
            Shipment.status != "delivered",
        )
        .order_by(Shipment.id)
    ).all()

    if not delayed_shipments:
        return DelayMonitorResult(0, 0, 0)

    shipment_ids = [shipment.id for shipment in delayed_shipments]

    if db.bind.dialect.name == "postgresql":
        rows = [
            {
                "shipment_id": shipment_id,
                "incident_type": "delivery_delay",
                "severity": "high",
                "status": "open",
            }
            for shipment_id in shipment_ids
        ]

        statement = pg_insert(Incident).values(rows)

        statement = statement.on_conflict_do_nothing(
            index_elements=[
                Incident.shipment_id,
                Incident.incident_type,
            ],
            index_where=Incident.status == "open",
        ).returning(Incident.id)

        created_ids = db.scalars(statement).all()
        created = len(created_ids)

    else:
        created = 0

        for shipment_id in shipment_ids:
            existing = db.scalar(
                select(Incident.id).where(
                    Incident.shipment_id == shipment_id,
                    Incident.incident_type == "delivery_delay",
                    Incident.status == "open",
                )
            )

            if existing is None:
                db.add(
                    Incident(
                        shipment_id=shipment_id,
                        incident_type="delivery_delay",
                        severity="high",
                        status="open",
                    )
                )
                db.flush()
                created += 1

    return DelayMonitorResult(
        delayed_shipments=len(shipment_ids),
        created_incidents=created,
        existing_incidents=len(shipment_ids) - created,
    )

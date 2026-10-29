from sqlalchemy import select
from sqlalchemy.orm import Session

from logiflow.models.delivery_event import DeliveryEvent
from logiflow.models.shipment import Shipment

ALLOWED_TRANSITIONS = {
    "pending": {"collected"},
    "collected": {"in_transit"},
    "in_transit": {"out_for_delivery"},
    "out_for_delivery": {"delivered", "delivery_failed"},
    "delivery_failed": {"out_for_delivery"},
    "delivered": set(),
}


class ShipmentNotFoundError(Exception):
    pass


class InvalidStatusTransitionError(Exception):
    pass


def update_shipment_status(
    db: Session,
    shipment_id: int,
    new_status: str,
    description: str | None = None,
) -> Shipment:
    """Atualiza uma entrega e registra seu evento de rastreamento."""

    shipment = db.scalar(
        select(Shipment).where(Shipment.id == shipment_id).with_for_update()
    )

    if shipment is None:
        raise ShipmentNotFoundError(f"Entrega {shipment_id} não encontrada.")

    current_status = shipment.status

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Transição inválida: {current_status} -> {new_status}"
        )

    shipment.status = new_status

    event = DeliveryEvent(
        shipment_id=shipment.id,
        event_type=new_status,
        description=description,
    )

    db.add(event)
    db.flush()

    return shipment

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from logiflow.api.schemas.shipment import (
    DeliveryEventResponse,
    ShipmentResponse,
    ShipmentStatusUpdate,
)
from logiflow.db.session import get_db
from logiflow.models.delivery_event import DeliveryEvent
from logiflow.models.shipment import Shipment
from logiflow.services.shipment_service import (
    InvalidStatusTransitionError,
    ShipmentNotFoundError,
    update_shipment_status,
)

router = APIRouter(prefix="/shipments", tags=["Shipments"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(shipment_id: int, db: DbSession):
    shipment = db.get(Shipment, shipment_id)

    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada.",
        )

    return shipment


@router.patch("/{shipment_id}/status", response_model=ShipmentResponse)
def change_shipment_status(
    shipment_id: int,
    payload: ShipmentStatusUpdate,
    db: DbSession,
):
    try:
        shipment = update_shipment_status(
            db=db,
            shipment_id=shipment_id,
            new_status=payload.status,
            description=payload.description,
        )

        db.commit()
        db.refresh(shipment)

        return shipment

    except ShipmentNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except InvalidStatusTransitionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise


@router.get(
    "/{shipment_id}/events",
    response_model=list[DeliveryEventResponse],
)
def get_shipment_events(shipment_id: int, db: DbSession):
    shipment = db.get(Shipment, shipment_id)

    if shipment is None:
        raise HTTPException(
            status_code=404,
            detail="Entrega não encontrada.",
        )

    events = db.scalars(
        select(DeliveryEvent)
        .where(DeliveryEvent.shipment_id == shipment_id)
        .order_by(DeliveryEvent.occurred_at, DeliveryEvent.id)
    ).all()

    return events

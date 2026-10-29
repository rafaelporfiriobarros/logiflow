from unittest.mock import MagicMock

import pytest

from logiflow.models.shipment import Shipment
from logiflow.services.shipment_service import (
    InvalidStatusTransitionError,
    ShipmentNotFoundError,
    update_shipment_status,
)


def test_valid_status_transition():
    db = MagicMock()

    shipment = Shipment(
        id=1,
        order_id=1,
        tracking_code="LOG123",
        status="pending",
    )

    db.scalar.return_value = shipment

    result = update_shipment_status(
        db=db,
        shipment_id=1,
        new_status="collected",
        description="Mercadoria coletada.",
    )

    assert result.status == "collected"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_invalid_status_transition():
    db = MagicMock()

    shipment = Shipment(
        id=1,
        order_id=1,
        tracking_code="LOG123",
        status="pending",
    )

    db.scalar.return_value = shipment

    with pytest.raises(InvalidStatusTransitionError):
        update_shipment_status(
            db=db,
            shipment_id=1,
            new_status="delivered",
        )

    db.add.assert_not_called()


def test_shipment_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    with pytest.raises(ShipmentNotFoundError):
        update_shipment_status(
            db=db,
            shipment_id=999,
            new_status="collected",
        )


def test_delivered_shipment_cannot_change():
    db = MagicMock()

    shipment = Shipment(
        id=1,
        order_id=1,
        tracking_code="LOG123",
        status="delivered",
    )

    db.scalar.return_value = shipment

    with pytest.raises(InvalidStatusTransitionError):
        update_shipment_status(
            db=db,
            shipment_id=1,
            new_status="in_transit",
        )

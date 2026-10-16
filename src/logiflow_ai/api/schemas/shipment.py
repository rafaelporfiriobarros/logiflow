from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShipmentStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    description: str | None = Field(default=None, max_length=255)


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    tracking_code: str
    status: str
    expected_delivery_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


class DeliveryEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shipment_id: int
    event_type: str
    description: str | None
    occurred_at: datetime

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MonitoringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str

    delayed_shipments: int
    created_incidents: int
    existing_incidents: int

    error_message: str | None


class MonitoringRunListResponse(BaseModel):
    items: list[MonitoringRunResponse]
    total: int
    limit: int
    offset: int

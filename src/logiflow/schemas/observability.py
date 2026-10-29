
from datetime import datetime

from pydantic import BaseModel, Field


class IncidentSummary(BaseModel):
    total: int = Field(ge=0)
    open: int = Field(ge=0)
    by_status: dict[str, int]


class NotificationSummary(BaseModel):
    total: int = Field(ge=0)
    pending: int = Field(ge=0)
    sending: int = Field(ge=0)
    sent: int = Field(ge=0)
    failed: int = Field(ge=0)
    success_rate_percent: float = Field(ge=0, le=100)
    attempts_by_status: dict[str, int]


class LatestMonitoringRun(BaseModel):
    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    delayed_shipments: int
    created_incidents: int
    existing_incidents: int
    error_message: str | None


class ObservabilitySummaryResponse(BaseModel):
    incidents: IncidentSummary
    notifications: NotificationSummary
    latest_monitoring_run: LatestMonitoringRun | None

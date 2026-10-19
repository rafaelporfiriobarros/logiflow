
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationClaimRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=50)
    notification_id: int | None = Field(default=None, ge=1)


class NotificationClaimItem(BaseModel):
    id: int
    incident_id: int
    channel: str
    recipient: str
    subject: str
    body: str
    attempts: int
    claim_token: UUID


class NotificationClaimResponse(BaseModel):
    items: list[NotificationClaimItem]
    total: int


class NotificationSentRequest(BaseModel):
    claim_token: UUID


class NotificationFailedRequest(BaseModel):
    claim_token: UUID
    error_message: str = Field(min_length=1, max_length=1000)


class NotificationStatusResponse(BaseModel):
    id: int
    status: str
    attempts: int
    next_attempt_at: datetime
    sent_at: datetime | None = None

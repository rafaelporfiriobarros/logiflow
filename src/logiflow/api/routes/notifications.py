
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from logiflow.api.dependencies.api_key import (
    require_monitoring_api_key,
)
from logiflow.core.config import get_settings
from logiflow.db.session import get_db
from logiflow.models.notification_outbox import NotificationOutbox
from logiflow.schemas.notifications import (
    NotificationClaimItem,
    NotificationClaimRequest,
    NotificationClaimResponse,
    NotificationFailedRequest,
    NotificationSentRequest,
    NotificationStatusResponse,
)
from logiflow.services.notification_queue import (
    InvalidNotificationClaimError,
    claim_notifications,
    mark_notification_failed,
    mark_notification_sent,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(require_monitoring_api_key)],
)



@router.post(
    "/claim",
    response_model=NotificationClaimResponse,
)
def claim_pending_notifications(
    payload: NotificationClaimRequest,
    db: Annotated[Session, Depends(get_db)],
):
    if (
        payload.notification_id is not None
        and get_settings().app_env != "development"
    ):
        raise HTTPException(
            status_code=403,
            detail="Targeted claims are only available in development",
        )

    try:
        notifications = claim_notifications(
            db,
            limit=payload.limit,
            notification_id=payload.notification_id,
        )

        items = [
            NotificationClaimItem(
                id=notification.id,
                incident_id=notification.incident_id,
                channel=notification.channel,
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
                attempts=notification.attempts,
                claim_token=notification.claim_token,
            )
            for notification in notifications
        ]

        db.commit()

        return NotificationClaimResponse(
            items=items,
            total=len(items),
        )

    except Exception:
        db.rollback()
        raise


@router.post(
    "/{notification_id}/sent",
    response_model=NotificationStatusResponse,
)
def confirm_notification_sent(
    notification_id: int,
    payload: NotificationSentRequest,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        mark_notification_sent(
            db,
            notification_id=notification_id,
            claim_token=payload.claim_token,
        )

        db.commit()

    except InvalidNotificationClaimError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

    notification = db.get(NotificationOutbox, notification_id)

    return NotificationStatusResponse.model_validate(
        notification,
        from_attributes=True,
    )


@router.post(
    "/{notification_id}/failed",
    response_model=NotificationStatusResponse,
)
def confirm_notification_failed(
    notification_id: int,
    payload: NotificationFailedRequest,
    db: Annotated[Session, Depends(get_db)],
):
    
    try:
        mark_notification_failed(
            db,
            notification_id=notification_id,
            claim_token=payload.claim_token,
            error_message=payload.error_message,
        )

        db.commit()

    except InvalidNotificationClaimError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

    notification = db.get(NotificationOutbox, notification_id)

    return NotificationStatusResponse.model_validate(
        notification,
        from_attributes=True,
    )
    
    



from sqlalchemy import func, select
from sqlalchemy.orm import Session

from logiflow_ai.models.incident import Incident
from logiflow_ai.models.monitoring_run import MonitoringRun
from logiflow_ai.models.notification_outbox import NotificationOutbox


def get_observability_summary(db: Session) -> dict:
    """Consolida indicadores operacionais do LogiFlow AI."""

    incident_rows = db.execute(
        select(Incident.status, func.count(Incident.id))
        .group_by(Incident.status)
    ).all()

    incident_counts = {
        status: count
        for status, count in incident_rows
    }

    notification_rows = db.execute(
        select(
            NotificationOutbox.status,
            func.count(NotificationOutbox.id),
            func.coalesce(func.sum(NotificationOutbox.attempts), 0),
        )
        .group_by(NotificationOutbox.status)
    ).all()

    notification_counts = {
        status: count
        for status, count, _ in notification_rows
    }

    attempts_by_status = {
        status: int(attempts)
        for status, _, attempts in notification_rows
    }

    total_notifications = sum(notification_counts.values())
    sent_notifications = notification_counts.get("sent", 0)

    success_rate = (
        round(sent_notifications / total_notifications * 100, 2)
        if total_notifications
        else 0.0
    )

    latest_run = db.scalar(
        select(MonitoringRun)
        .order_by(
            MonitoringRun.started_at.desc(),
            MonitoringRun.id.desc(),
        )
        .limit(1)
    )

    monitoring = None

    if latest_run is not None:
        monitoring = {
            "id": latest_run.id,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "finished_at": latest_run.finished_at,
            "delayed_shipments": latest_run.delayed_shipments,
            "created_incidents": latest_run.created_incidents,
            "existing_incidents": latest_run.existing_incidents,
            "error_message": latest_run.error_message,
        }

    return {
        "incidents": {
            "total": sum(incident_counts.values()),
            "open": incident_counts.get("open", 0),
            "by_status": incident_counts,
        },
        "notifications": {
            "total": total_notifications,
            "pending": notification_counts.get("pending", 0),
            "sending": notification_counts.get("sending", 0),
            "sent": sent_notifications,
            "failed": notification_counts.get("failed", 0),
            "success_rate_percent": success_rate,
            "attempts_by_status": attempts_by_status,
        },
        "latest_monitoring_run": monitoring,
    }

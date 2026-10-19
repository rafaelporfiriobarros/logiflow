
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from logiflow_ai.models.incident import Incident
from logiflow_ai.models.notification_outbox import NotificationOutbox
from logiflow_ai.models.shipment import Shipment


def enqueue_incident_notifications(
    db: Session,
    incident_ids: list[int],
    recipient: str,
) -> int:
    """Cria notificações pendentes sem executar commit."""

    if not incident_ids:
        return 0

    if not recipient or not recipient.strip():
        raise ValueError("Destinatário não configurado.")

    incidents = db.execute(
        select(Incident, Shipment.tracking_code)
        .join(Shipment, Shipment.id == Incident.shipment_id)
        .where(Incident.id.in_(incident_ids))
    ).all()

    rows = [
        {
            "incident_id": incident.id,
            "channel": "email",
            "status": "pending",
            "recipient": recipient,
            "subject": (
                f"[LogiFlow AI] Atraso na remessa {tracking_code}"
            ),
            "body": (
                f"Incidente #{incident.id}\n"
                f"Remessa: {tracking_code}\n"
                f"Tipo: {incident.incident_type}\n"
                f"Severidade: {incident.severity}\n"
                "Status: aguardando tratamento operacional."
            ),
        }
        for incident, tracking_code in incidents
    ]

    if not rows:
        return 0

    if db.bind.dialect.name == "postgresql":
        statement = pg_insert(NotificationOutbox).values(rows)

        statement = statement.on_conflict_do_nothing(
            constraint="uq_notification_outbox_incident_channel"
        ).returning(NotificationOutbox.id)

        return len(db.scalars(statement).all())

    created = 0

    for row in rows:
        existing = db.scalar(
            select(NotificationOutbox.id).where(
                NotificationOutbox.incident_id == row["incident_id"],
                NotificationOutbox.channel == row["channel"],
            )
        )

        if existing is None:
            db.add(NotificationOutbox(**row))
            created += 1

    db.flush()
    return created

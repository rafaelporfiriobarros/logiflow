from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from logiflow.models.incident import Incident


class IncidentNotFoundError(Exception):
    pass


class IncidentAlreadyResolvedError(Exception):
    pass


@dataclass(frozen=True)
class IncidentPage:
    items: list[Incident]
    total: int
    limit: int
    offset: int


def get_incident(
    db: Session,
    incident_id: int,
) -> Incident:
    incident = db.get(Incident, incident_id)

    if incident is None:
        raise IncidentNotFoundError(f"Incidente {incident_id} não encontrado.")

    return incident


def list_incidents(
    db: Session,
    status: str | None = None,
    severity: str | None = None,
    shipment_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> IncidentPage:
    filters = []

    if status is not None:
        filters.append(Incident.status == status)

    if severity is not None:
        filters.append(Incident.severity == severity)

    if shipment_id is not None:
        filters.append(Incident.shipment_id == shipment_id)

    total = db.scalar(select(func.count()).select_from(Incident).where(*filters)) or 0

    incidents = db.scalars(
        select(Incident)
        .where(*filters)
        .order_by(
            Incident.created_at.desc(),
            Incident.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()

    return IncidentPage(
        items=list(incidents),
        total=total,
        limit=limit,
        offset=offset,
    )


def resolve_incident(
    db: Session,
    incident_id: int,
) -> Incident:
    incident = db.scalar(
        select(Incident).where(Incident.id == incident_id).with_for_update()
    )

    if incident is None:
        raise IncidentNotFoundError(f"Incidente {incident_id} não encontrado.")

    if incident.status == "resolved":
        raise IncidentAlreadyResolvedError(
            f"Incidente {incident_id} já está resolvido."
        )

    if incident.status != "open":
        raise ValueError(
            f"Não é possível resolver um incidente com status '{incident.status}'."
        )

    incident.status = "resolved"
    db.flush()

    return incident

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from logiflow_ai.db.session import get_db
from logiflow_ai.schemas.incident import (
    IncidentListResponse,
    IncidentResponse,
)
from logiflow_ai.services.incident_service import (
    IncidentAlreadyResolvedError,
    IncidentNotFoundError,
    get_incident,
    list_incidents,
    resolve_incident,
)

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"],
)


@router.get(
    "",
    response_model=IncidentListResponse,
)
def list_incidents_endpoint(
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[
        str | None,
        Query(pattern="^(open|resolved)$"),
    ] = None,
    severity: Annotated[
        str | None,
        Query(pattern="^(low|medium|high|critical)$"),
    ] = None,
    shipment_id: Annotated[
        int | None,
        Query(ge=1),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
):
    result = list_incidents(
        db=db,
        status=status,
        severity=severity,
        shipment_id=shipment_id,
        limit=limit,
        offset=offset,
    )

    return result


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
)
def get_incident_endpoint(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return get_incident(db, incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{incident_id}/resolve",
    response_model=IncidentResponse,
)
def resolve_incident_endpoint(
    incident_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        incident = resolve_incident(db, incident_id)

        db.commit()
        db.refresh(incident)

        return incident

    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except IncidentAlreadyResolvedError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception:
        db.rollback()
        raise

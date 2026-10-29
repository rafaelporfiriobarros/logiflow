from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session, sessionmaker

from logiflow.api.dependencies.api_key import (
    require_monitoring_api_key,
)
from logiflow.db.session import get_db
from logiflow.schemas.monitoring import (
    MonitoringRunListResponse,
    MonitoringRunResponse,
)
from logiflow.services.monitoring_service import (
    MonitoringRunNotFoundError,
    execute_delay_monitoring,
    get_monitoring_run,
    list_monitoring_runs,
)

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"],
    dependencies=[Depends(require_monitoring_api_key)],
)


@router.post(
    "/delays",
    response_model=MonitoringRunResponse,
    status_code=201,
)
def run_delay_monitoring(
    db: Annotated[Session, Depends(get_db)],
):
    # Utiliza o mesmo engine da sessão configurada
    # para esta aplicação.
    factory = sessionmaker(
        bind=db.get_bind(),
        expire_on_commit=False,
    )

    return execute_delay_monitoring(factory)


@router.get(
    "/runs",
    response_model=MonitoringRunListResponse,
)
def get_runs(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = list_monitoring_runs(
        db,
        limit=limit,
        offset=offset,
    )

    return MonitoringRunListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/runs/{run_id}",
    response_model=MonitoringRunResponse,
)
def get_run(
    run_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    try:
        return get_monitoring_run(db, run_id)

    except MonitoringRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

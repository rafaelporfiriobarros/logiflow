
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from logiflow_ai.api.dependencies.api_key import (
    require_monitoring_api_key,
)
from logiflow_ai.db.session import get_db
from logiflow_ai.schemas.observability import (
    ObservabilitySummaryResponse,
)
from logiflow_ai.services.observability import (
    get_observability_summary,
)

router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
    dependencies=[Depends(require_monitoring_api_key)],
)


@router.get(
    "/summary",
    response_model=ObservabilitySummaryResponse,
)
def read_observability_summary(
    db: Annotated[Session, Depends(get_db)],
) -> ObservabilitySummaryResponse:
    summary = get_observability_summary(db)

    return ObservabilitySummaryResponse.model_validate(summary)

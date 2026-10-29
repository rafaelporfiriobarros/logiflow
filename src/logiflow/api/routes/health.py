from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from logiflow.db.session import get_db

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": "logiflow-api",
    }


@router.get("/database")
def database_health(db: DbSession):
    try:
        result = db.execute(text("SELECT 1")).scalar_one()

        return {
            "status": "healthy",
            "database": "postgresql",
            "connection": result == 1,
        }

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from exc

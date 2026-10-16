from fastapi import FastAPI

from logiflow_ai.api.routes import incidents, monitoring
from logiflow_ai.api.routes.health import router as health_router
from logiflow_ai.api.routes.shipments import router as shipments_router
from logiflow_ai.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Plataforma de automação, integrações e inteligência artificial para logística."
    ),
)

app.include_router(
    monitoring.router,
    prefix="/api/v1",
)

app.include_router(
    incidents.router,
    prefix="/api/v1",
)
app.include_router(shipments_router, prefix="/api/v1")

app.include_router(
    health_router,
    prefix="/api/v1",
)


@app.get("/", tags=["Root"])
def root():
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "documentation": "/docs",
    }

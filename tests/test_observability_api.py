
from fastapi import FastAPI
from fastapi.testclient import TestClient

from logiflow.api.routes import observability
from logiflow.db.session import get_db


def create_test_client():
    app = FastAPI()
    app.include_router(
        observability.router,
        prefix="/api/v1",
    )

    app.dependency_overrides[get_db] = lambda: None

    return app


def test_observability_requires_api_key(monkeypatch):
    monkeypatch.setattr(
        "logiflow.api.dependencies.api_key.get_expected_api_key",
        lambda: "test-secret-key",
    )

    app = create_test_client()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/observability/summary"
        )

    assert response.status_code == 401


def test_observability_returns_summary(monkeypatch):
    monkeypatch.setattr(
        "logiflow.api.dependencies.api_key.get_expected_api_key",
        lambda: "test-secret-key",
    )

    monkeypatch.setattr(
        observability,
        "get_observability_summary",
        lambda db: {
            "incidents": {
                "total": 10,
                "open": 4,
                "by_status": {
                    "open": 4,
                    "resolved": 6,
                },
            },
            "notifications": {
                "total": 4,
                "pending": 0,
                "sending": 0,
                "sent": 3,
                "failed": 1,
                "success_rate_percent": 75.0,
                "attempts_by_status": {
                    "sent": 4,
                    "failed": 3,
                },
            },
            "latest_monitoring_run": None,
        },
    )

    app = create_test_client()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/observability/summary",
            headers={
                "X-API-Key": "test-secret-key",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["incidents"]["open"] == 4
    assert data["notifications"]["total"] == 4
    assert data["notifications"]["sent"] == 3
    assert data["notifications"]["failed"] == 1
    assert data["notifications"]["success_rate_percent"] == 75.0


def test_observability_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setattr(
        "logiflow.api.dependencies.api_key.get_expected_api_key",
        lambda: "test-secret-key",
    )

    app = create_test_client()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/observability/summary",
            headers={
                "X-API-Key": "invalid-key",
            },
        )

    assert response.status_code == 401

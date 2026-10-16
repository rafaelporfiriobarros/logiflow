from fastapi.testclient import TestClient

from logiflow_ai.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["application"] == "LogiFlow AI"
    assert data["version"] == "0.1.0"
    assert data["documentation"] == "/docs"


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    assert response.json() == {
        "status": "healthy",
        "service": "logiflow-api",
    }


def test_database_health():
    response = client.get("/api/v1/health/database")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["database"] == "postgresql"
    assert data["connection"] is True

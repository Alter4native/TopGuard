from fastapi.testclient import TestClient

from src.main import app


def test_backend_health() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "backend"
    assert payload["status"] == "ok"
    assert payload["retention_days"] == 30
    assert payload["api"]["auth"] == "enabled"
    assert payload["api"]["internal"] == "service-token"

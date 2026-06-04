from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def login(username: str, password: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


def auth_headers(username: str = "admin", password: str = "admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {login(username, password)}"}


def test_auth_login_refresh_and_me() -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})

    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me = client.get("/api/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]


def test_invalid_login_is_rejected() -> None:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})

    assert response.status_code == 401


def test_camera_api_and_rbac() -> None:
    viewer_headers = auth_headers("viewer", "viewer")
    operator_headers = auth_headers("operator", "operator")

    viewer_list = client.get("/api/cameras", headers=viewer_headers)
    assert viewer_list.status_code == 200
    assert len(viewer_list.json()) >= 1

    forbidden = client.post(
        "/api/cameras",
        headers=viewer_headers,
        json={"name": "Forbidden camera"},
    )
    assert forbidden.status_code == 403

    created = client.post(
        "/api/cameras",
        headers=operator_headers,
        json={
            "name": "RTSP camera",
            "source_type": "rtsp",
            "source_uri": "rtsp://camera.local/stream",
            "processing_fps": 4,
        },
    )
    assert created.status_code == 200
    camera = created.json()
    assert camera["name"] == "RTSP camera"

    updated = client.patch(
        f"/api/cameras/{camera['camera_id']}",
        headers=operator_headers,
        json={"processing_fps": 6},
    )
    assert updated.status_code == 200
    assert updated.json()["processing_fps"] == 6


def test_internal_event_ingest_and_public_event_filters() -> None:
    admin_headers = auth_headers()
    service_headers = {"Authorization": "Bearer change-me-internal-token"}

    unauthorized = client.post("/internal/events", json={"events": []})
    assert unauthorized.status_code == 401

    event_timestamp = datetime(2026, 5, 21, tzinfo=timezone.utc).isoformat()
    ingested = client.post(
        "/internal/events",
        headers=service_headers,
        json={
            "events": [
                {
                    "event_id": "event-stage7-1",
                    "camera_id": "camera-stage7",
                    "event_type": "person_detected",
                    "timestamp": event_timestamp,
                    "confidence": 0.91,
                    "snapshot_url": "camera-stage7/2026/05/21/event-stage7-1.jpg",
                    "metadata": {"track_id": 12},
                }
            ]
        },
    )
    assert ingested.status_code == 200
    assert ingested.json()[0]["event_id"] == "event-stage7-1"

    listed = client.get(
        "/api/events",
        headers=admin_headers,
        params={"camera_id": "camera-stage7", "event_type": "person_detected"},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["event_id"] == "event-stage7-1"

    detail = client.get("/api/events/event-stage7-1", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["metadata"]["track_id"] == 12

    snapshot = client.get("/api/events/event-stage7-1/snapshot", headers=admin_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["snapshot_storage_key"] == "camera-stage7/2026/05/21/event-stage7-1.jpg"


def test_internal_camera_status_update() -> None:
    admin_headers = auth_headers()
    service_headers = {"Authorization": "Bearer change-me-internal-token"}

    cameras = client.get("/api/cameras", headers=admin_headers).json()
    camera_id = cameras[0]["camera_id"]

    response = client.patch(
        f"/internal/cameras/{camera_id}/status",
        headers=service_headers,
        json={"state": "offline", "last_error": "read timeout"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "offline"
    assert response.json()["last_error"] == "read timeout"


def test_person_api_is_operator_or_admin_only() -> None:
    viewer_headers = auth_headers("viewer", "viewer")
    operator_headers = auth_headers("operator", "operator")

    forbidden = client.get("/api/persons", headers=viewer_headers)
    assert forbidden.status_code == 403

    created = client.post(
        "/api/persons",
        headers=operator_headers,
        json={"display_name": "Known Person", "external_id": "employee-1"},
    )
    assert created.status_code == 200
    person = created.json()
    assert person["display_name"] == "Known Person"

    uploaded = client.post(
        f"/api/persons/{person['person_id']}/photos",
        headers=operator_headers,
        files={"file": ("face.jpg", b"fake-image", "image/jpeg")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["filename"] == "face.jpg"

    embedding = client.post(
        f"/api/persons/{person['person_id']}/embeddings",
        headers=operator_headers,
        json={
            "photo_id": uploaded.json()["photo_id"],
            "embedding_model": "simple-hash-face-embedding",
            "embedding_dim": 32,
            "vector_collection": "person_face_embeddings",
            "threshold": 0.65,
        },
    )
    assert embedding.status_code == 200
    assert embedding.json()["person_id"] == person["person_id"]
    assert embedding.json()["embedding_dim"] == 32


def test_models_and_settings_api() -> None:
    viewer_headers = auth_headers("viewer", "viewer")
    operator_headers = auth_headers("operator", "operator")

    models = client.get("/api/models", headers=viewer_headers)
    assert models.status_code == 200
    assert models.json()[0]["runtime"] == "yolo"

    settings = client.get("/api/settings", headers=viewer_headers)
    assert settings.status_code == 200
    assert settings.json()["retention_days"] == 30

    quality = client.get("/api/models/quality", headers=viewer_headers)
    assert quality.status_code == 200
    payload = quality.json()
    assert payload["status"] == "available"
    assert payload["dataset"]["models"] >= 1
    assert [algorithm["algorithm"] for algorithm in payload["algorithms"]] == ["DBSCAN", "K-Means"]
    assert all(algorithm["analysis"] for algorithm in payload["algorithms"])

    forbidden = client.patch(
        "/api/settings",
        headers=viewer_headers,
        json={"processing_fps": 7},
    )
    assert forbidden.status_code == 403

    updated = client.patch(
        "/api/settings",
        headers=operator_headers,
        json={"processing_fps": 7},
    )
    assert updated.status_code == 200
    assert updated.json()["processing_fps"] == 7

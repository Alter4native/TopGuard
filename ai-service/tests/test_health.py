from fastapi.testclient import TestClient

from app.main import app


def test_ai_health() -> None:
    client = TestClient(app)

    response = client.get("/ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "ai-service"
    assert payload["status"] == "ok"
    assert payload["camera"]["status"]["state"] == "stopped"
    assert payload["detector"] == {
        "runtime": "yolo",
        "model_path": "/app/models/yolo-person.pt",
        "scope": "person-only",
        "confidence_threshold": 0.5,
        "loaded": False,
    }
    assert payload["tracker"] == {
        "runtime": "bytetrack",
        "active_tracks": 0,
        "match_threshold": 0.3,
        "track_ttl_frames": 30,
        "new_track_threshold": 0.5,
    }
    assert payload["recognition"] == {
        "runtime": "simple",
        "model_name": "simple-hash-face-embedding",
        "embedding_dim": 32,
        "threshold": 0.65,
        "enrolled_embeddings": 0,
        "embedding_store": {
            "runtime": "memory",
            "collection": None,
            "status": "ready",
            "last_error": None,
        },
        "person_reid_enabled": False,
    }
    assert payload["events"] == {
        "pending_published_events": 0,
        "cooldown_keys": 0,
        "restricted_zones": 0,
    }


def test_camera_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/camera/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["camera_id"] == "local-camera"
    assert payload["source_type"] == "webcam"
    assert payload["processing_fps"] == 5


def test_detector_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/detector/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "yolo"
    assert payload["scope"] == "person-only"
    assert payload["loaded"] is False


def test_tracker_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/tracker/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "bytetrack"
    assert payload["active_tracks"] == 0
    assert payload["track_ttl_frames"] == 30


def test_events_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/events/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pending_published_events"] == 0
    assert payload["cooldown_keys"] == 0
    assert payload["restricted_zones"] == 0


def test_recognition_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/recognition/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime"] == "simple"
    assert payload["embedding_dim"] == 32
    assert payload["threshold"] == 0.65


def test_vector_status_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ai/vector/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "runtime": "memory",
        "collection": None,
        "status": "ready",
        "last_error": None,
    }

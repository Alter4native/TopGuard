from fastapi import FastAPI

from app.config import get_settings
from app.detection.factory import build_detector
from app.events.engine import EventEngine
from app.events.schemas import EventRuleConfig
from app.recognition.factory import build_face_recognizer
from app.tracking.factory import build_tracker
from app.video.manager import CameraConfig, CameraManager

settings = get_settings()
camera_manager = CameraManager(
    CameraConfig(
        camera_id=settings.camera_id,
        source_type=settings.camera_source_type,
        source_uri=settings.camera_source_uri,
        processing_fps=settings.processing_fps,
        reconnect_backoff_seconds=settings.reconnect_backoff_seconds,
        max_reconnect_backoff_seconds=settings.max_reconnect_backoff_seconds,
        open_timeout_ms=settings.camera_open_timeout_ms,
        read_timeout_ms=settings.camera_read_timeout_ms,
    )
)
detector = build_detector(
    runtime=settings.detector_runtime,
    model_path=settings.model_path,
    confidence_threshold=settings.person_confidence_threshold,
)
tracker = build_tracker(
    runtime=settings.tracker_runtime,
    match_threshold=settings.tracker_match_threshold,
    track_ttl_frames=settings.track_ttl_frames,
    new_track_threshold=settings.tracker_new_track_threshold,
)
face_recognizer = build_face_recognizer(
    runtime=settings.face_recognition_runtime,
    threshold=settings.face_recognition_threshold,
    embedding_dim=settings.face_embedding_dim,
    model_name=settings.face_embedding_model_name,
    embedding_store_runtime=settings.embedding_store_runtime,
    qdrant_url=settings.qdrant_url,
    qdrant_collection_name=settings.qdrant_collection_person_face_embeddings,
    qdrant_api_key=settings.qdrant_api_key,
    qdrant_timeout_seconds=settings.qdrant_timeout_seconds,
)
event_engine = EventEngine(
    config=EventRuleConfig(
        person_cooldown_seconds=settings.event_cooldown_seconds,
        known_person_cooldown_seconds=settings.known_person_event_cooldown_seconds,
        unknown_person_cooldown_seconds=settings.unknown_person_event_cooldown_seconds,
        restricted_zone_cooldown_seconds=settings.restricted_zone_event_cooldown_seconds,
        camera_offline_cooldown_seconds=settings.camera_offline_event_cooldown_seconds,
        people_count_interval_seconds=settings.people_count_interval_seconds,
    )
)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/ai/docs",
    openapi_url="/ai/openapi.json",
)


def health_payload() -> dict[str, object]:
    return {
        "service": "ai-service",
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
        "camera": {
            "camera_id": settings.camera_id,
            "source_type": settings.camera_source_type,
            "source_uri": settings.camera_source_uri,
            "processing_fps": settings.processing_fps,
            "status": camera_manager.get_status(),
        },
        "detector": detector.metadata().as_dict(),
        "tracker": tracker.metadata().as_dict(),
        "recognition": face_recognizer.metadata().as_dict(),
        "events": event_engine.metadata().as_dict(),
    }


@app.get("/health", tags=["health"])
def health() -> dict[str, object]:
    return health_payload()


@app.get("/ai/health", tags=["health"])
def prefixed_health() -> dict[str, object]:
    return health_payload()


@app.get("/ai/camera/status", tags=["camera"])
def camera_status() -> dict[str, object]:
    return camera_manager.get_status()


@app.get("/ai/detector/status", tags=["detector"])
def detector_status() -> dict[str, object]:
    return detector.metadata().as_dict()


@app.get("/ai/tracker/status", tags=["tracker"])
def tracker_status() -> dict[str, object]:
    return tracker.metadata().as_dict()


@app.get("/ai/events/status", tags=["events"])
def events_status() -> dict[str, object]:
    return event_engine.metadata().as_dict()


@app.get("/ai/recognition/status", tags=["recognition"])
def recognition_status() -> dict[str, object]:
    return face_recognizer.metadata().as_dict()


@app.get("/ai/vector/status", tags=["recognition"])
def vector_status() -> dict[str, object]:
    return face_recognizer.metadata().embedding_store.as_dict()

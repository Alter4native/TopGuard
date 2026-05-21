from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from app.detection.schemas import BoundingBox
from app.events.schemas import RecognitionResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecognitionDecision(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FaceEmbedding:
    vector: tuple[float, ...]
    model_name: str
    embedding_dim: int

    def __post_init__(self) -> None:
        if len(self.vector) != self.embedding_dim:
            raise ValueError("Embedding vector length must match embedding_dim")


@dataclass(frozen=True)
class PersonEmbedding:
    person_id: str
    embedding: FaceEmbedding
    photo_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class FaceMatch:
    person_id: str | None
    score: float
    threshold: float
    decision: RecognitionDecision

    @property
    def is_known(self) -> bool:
        return self.decision == RecognitionDecision.KNOWN and self.person_id is not None


@dataclass(frozen=True)
class FaceRecognitionInput:
    camera_id: str
    track_id: int
    image: Any
    face_bbox: BoundingBox | None = None


@dataclass(frozen=True)
class FaceRecognitionOutput:
    camera_id: str
    track_id: int
    decision: RecognitionDecision
    score: float
    threshold: float
    person_id: str | None
    face_bbox: BoundingBox

    def to_event_result(self) -> RecognitionResult:
        return RecognitionResult(
            camera_id=self.camera_id,
            track_id=self.track_id,
            is_known=self.decision == RecognitionDecision.KNOWN,
            score=self.score,
            threshold=self.threshold,
            person_id=self.person_id,
            face_bbox=self.face_bbox,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "decision": self.decision.value,
            "score": self.score,
            "threshold": self.threshold,
            "person_id": self.person_id,
            "face_bbox": self.face_bbox.as_dict(),
        }


@dataclass(frozen=True)
class EmbeddingStoreMetadata:
    runtime: str
    collection: str | None
    status: str
    last_error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "collection": self.collection,
            "status": self.status,
            "last_error": self.last_error,
        }


@dataclass(frozen=True)
class FaceRecognizerMetadata:
    runtime: str
    model_name: str
    embedding_dim: int
    threshold: float
    enrolled_embeddings: int
    embedding_store: EmbeddingStoreMetadata
    person_reid_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "threshold": self.threshold,
            "enrolled_embeddings": self.enrolled_embeddings,
            "embedding_store": self.embedding_store.as_dict(),
            "person_reid_enabled": self.person_reid_enabled,
        }

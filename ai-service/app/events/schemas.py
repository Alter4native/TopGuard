from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from app.detection.schemas import BoundingBox


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventType(StrEnum):
    PERSON_DETECTED = "person_detected"
    KNOWN_PERSON_DETECTED = "known_person_detected"
    UNKNOWN_PERSON_DETECTED = "unknown_person_detected"
    RESTRICTED_ZONE_ENTRY = "restricted_zone_entry"
    CAMERA_OFFLINE = "camera_offline"
    PEOPLE_COUNT = "people_count"


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class RestrictedZone:
    zone_id: str
    name: str
    polygon: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.polygon) < 3:
            raise ValueError("RestrictedZone polygon must contain at least 3 points")

    def as_dict(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "name": self.name,
            "polygon": [point.as_dict() for point in self.polygon],
        }


@dataclass(frozen=True)
class RecognitionResult:
    camera_id: str
    track_id: int
    is_known: bool
    score: float
    threshold: float
    person_id: str | None = None
    face_bbox: BoundingBox | None = None


@dataclass(frozen=True)
class EventRuleConfig:
    person_cooldown_seconds: int = 60
    known_person_cooldown_seconds: int = 120
    unknown_person_cooldown_seconds: int = 120
    restricted_zone_cooldown_seconds: int = 300
    camera_offline_cooldown_seconds: int = 300
    people_count_interval_seconds: int = 10

    def cooldown_for(self, event_type: EventType) -> int:
        return {
            EventType.PERSON_DETECTED: self.person_cooldown_seconds,
            EventType.KNOWN_PERSON_DETECTED: self.known_person_cooldown_seconds,
            EventType.UNKNOWN_PERSON_DETECTED: self.unknown_person_cooldown_seconds,
            EventType.RESTRICTED_ZONE_ENTRY: self.restricted_zone_cooldown_seconds,
            EventType.CAMERA_OFFLINE: self.camera_offline_cooldown_seconds,
            EventType.PEOPLE_COUNT: self.people_count_interval_seconds,
        }[event_type]


@dataclass
class VisionEvent:
    camera_id: str
    event_type: EventType
    confidence: float
    metadata: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)
    snapshot_url: str | None = None

    def with_snapshot(self, snapshot_url: str | None) -> "VisionEvent":
        self.snapshot_url = snapshot_url
        return self

    def as_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "snapshot_url": self.snapshot_url,
            "metadata": self.metadata,
        }


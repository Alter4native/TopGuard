from dataclasses import dataclass
from datetime import datetime

from app.video.source import VideoFrame


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("BoundingBox max coordinates must be greater than min coordinates")

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def as_xyxy(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    def as_dict(self) -> dict[str, float]:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class Detection:
    camera_id: str
    frame_sequence: int
    timestamp: datetime
    bbox: BoundingBox
    class_id: int
    class_name: str
    confidence: float

    @classmethod
    def from_frame(
        cls,
        frame: VideoFrame,
        bbox: BoundingBox,
        class_id: int,
        class_name: str,
        confidence: float,
    ) -> "Detection":
        return cls(
            camera_id=frame.camera_id,
            frame_sequence=frame.sequence,
            timestamp=frame.timestamp,
            bbox=bbox,
            class_id=class_id,
            class_name=class_name,
            confidence=confidence,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "camera_id": self.camera_id,
            "frame_sequence": self.frame_sequence,
            "timestamp": self.timestamp.isoformat(),
            "bbox": self.bbox.as_dict(),
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class DetectorMetadata:
    runtime: str
    model_path: str
    scope: str
    confidence_threshold: float
    loaded: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "runtime": self.runtime,
            "model_path": self.model_path,
            "scope": self.scope,
            "confidence_threshold": self.confidence_threshold,
            "loaded": self.loaded,
        }


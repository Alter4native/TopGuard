"""Detection package."""

from app.detection.base import ObjectDetector
from app.detection.schemas import BoundingBox, Detection, DetectorMetadata

__all__ = ["BoundingBox", "Detection", "DetectorMetadata", "ObjectDetector"]


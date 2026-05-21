from abc import ABC, abstractmethod
from typing import Sequence

from app.detection.schemas import Detection, DetectorMetadata
from app.video.source import VideoFrame


PERSON_CLASS_NAME = "person"


class ObjectDetector(ABC):
    @abstractmethod
    def detect(self, frame: VideoFrame) -> Sequence[Detection]:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> DetectorMetadata:
        raise NotImplementedError


def is_allowed_person_detection(
    class_name: str,
    confidence: float,
    confidence_threshold: float,
) -> bool:
    return class_name == PERSON_CLASS_NAME and confidence >= confidence_threshold


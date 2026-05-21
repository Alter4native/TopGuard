from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.detection.schemas import Detection
from app.tracking.schemas import TrackedObject, TrackerMetadata


class ObjectTracker(ABC):
    @abstractmethod
    def update(
        self,
        camera_id: str,
        frame_sequence: int,
        detections: Sequence[Detection],
    ) -> Sequence[TrackedObject]:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> TrackerMetadata:
        raise NotImplementedError


from collections.abc import Sequence

from app.detection.base import ObjectDetector
from app.detection.schemas import Detection, DetectorMetadata
from app.video.source import VideoFrame


class MockPersonDetector(ObjectDetector):
    def __init__(self, detections: Sequence[Detection] | None = None) -> None:
        self._detections = list(detections or [])

    def detect(self, frame: VideoFrame) -> Sequence[Detection]:
        return [
            Detection(
                camera_id=frame.camera_id,
                frame_sequence=frame.sequence,
                timestamp=frame.timestamp,
                bbox=detection.bbox,
                class_id=detection.class_id,
                class_name=detection.class_name,
                confidence=detection.confidence,
            )
            for detection in self._detections
        ]

    def metadata(self) -> DetectorMetadata:
        return DetectorMetadata(
            runtime="mock",
            model_path="mock",
            scope="person-only",
            confidence_threshold=0.0,
            loaded=True,
        )


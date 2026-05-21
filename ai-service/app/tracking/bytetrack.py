from collections.abc import Sequence
from dataclasses import dataclass, field

from app.detection.base import PERSON_CLASS_NAME
from app.detection.schemas import Detection
from app.tracking.base import ObjectTracker
from app.tracking.schemas import TrackedObject, TrackerMetadata
from app.tracking.state import Track, bbox_iou


@dataclass(frozen=True)
class ByteTrackConfig:
    match_threshold: float = 0.3
    track_ttl_frames: int = 30
    new_track_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not 0 <= self.match_threshold <= 1:
            raise ValueError("match_threshold must be between 0 and 1")
        if self.track_ttl_frames < 0:
            raise ValueError("track_ttl_frames must be greater than or equal to 0")
        if not 0 <= self.new_track_threshold <= 1:
            raise ValueError("new_track_threshold must be between 0 and 1")


@dataclass
class CameraTrackState:
    tracks: dict[int, Track] = field(default_factory=dict)
    next_track_id: int = 1

    def create_track(self, detection: Detection) -> Track:
        track = Track(
            track_id=self.next_track_id,
            camera_id=detection.camera_id,
            bbox=detection.bbox,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
            last_frame_sequence=detection.frame_sequence,
            last_seen_at=detection.timestamp,
        )
        self.tracks[track.track_id] = track
        self.next_track_id += 1
        return track


class ByteTrackTracker(ObjectTracker):
    """Dependency-light ByteTrack-style IoU tracker for MVP event dedup.

    It keeps the ByteTrack ownership boundary and config shape while avoiding
    model/runtime coupling in unit tests. Stage 13 can swap this implementation
    for an optimized tracker backend without changing the public tracking
    contract.
    """

    def __init__(self, config: ByteTrackConfig | None = None) -> None:
        self.config = config or ByteTrackConfig()
        self._camera_states: dict[str, CameraTrackState] = {}

    def update(
        self,
        camera_id: str,
        frame_sequence: int,
        detections: Sequence[Detection],
    ) -> Sequence[TrackedObject]:
        state = self._camera_states.setdefault(camera_id, CameraTrackState())
        self._purge_expired_tracks(state, frame_sequence)

        person_detections = [
            detection
            for detection in detections
            if detection.camera_id == camera_id
            and detection.class_name == PERSON_CLASS_NAME
            and detection.confidence >= self.config.new_track_threshold
        ]
        person_detections.sort(key=lambda detection: detection.confidence, reverse=True)

        matched_track_ids: set[int] = set()
        tracked_objects: list[TrackedObject] = []

        for detection in person_detections:
            track = self._match_track(state, detection, matched_track_ids)
            if track is None:
                track = state.create_track(detection)
            else:
                track.update(detection)

            matched_track_ids.add(track.track_id)
            tracked_objects.append(
                TrackedObject.from_detection(
                    detection=detection,
                    track_id=track.track_id,
                    hits=track.hits,
                )
            )

        return tracked_objects

    def metadata(self) -> TrackerMetadata:
        return TrackerMetadata(
            runtime="bytetrack",
            active_tracks=sum(len(state.tracks) for state in self._camera_states.values()),
            match_threshold=self.config.match_threshold,
            track_ttl_frames=self.config.track_ttl_frames,
            new_track_threshold=self.config.new_track_threshold,
        )

    def _match_track(
        self,
        state: CameraTrackState,
        detection: Detection,
        matched_track_ids: set[int],
    ) -> Track | None:
        best_track: Track | None = None
        best_iou = 0.0

        for track in state.tracks.values():
            if track.track_id in matched_track_ids:
                continue
            if track.class_name != detection.class_name:
                continue

            iou = bbox_iou(track.bbox, detection.bbox)
            if iou >= self.config.match_threshold and iou > best_iou:
                best_iou = iou
                best_track = track

        return best_track

    def _purge_expired_tracks(self, state: CameraTrackState, frame_sequence: int) -> None:
        expired_track_ids = [
            track_id
            for track_id, track in state.tracks.items()
            if track.is_expired(frame_sequence=frame_sequence, ttl_frames=self.config.track_ttl_frames)
        ]
        for track_id in expired_track_ids:
            del state.tracks[track_id]


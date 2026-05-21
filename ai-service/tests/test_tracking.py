from datetime import datetime, timezone

import pytest

from app.detection.schemas import BoundingBox, Detection
from app.tracking.bytetrack import ByteTrackConfig, ByteTrackTracker
from app.tracking.factory import build_tracker
from app.tracking.state import bbox_iou


def make_detection(
    frame_sequence: int,
    bbox: BoundingBox,
    camera_id: str = "camera-1",
    confidence: float = 0.9,
    class_name: str = "person",
) -> Detection:
    return Detection(
        camera_id=camera_id,
        frame_sequence=frame_sequence,
        timestamp=datetime(2026, 5, 21, tzinfo=timezone.utc),
        bbox=bbox,
        class_id=0 if class_name == "person" else 2,
        class_name=class_name,
        confidence=confidence,
    )


def test_bbox_iou_returns_expected_overlap() -> None:
    left = BoundingBox(x1=0, y1=0, x2=100, y2=100)
    right = BoundingBox(x1=50, y1=50, x2=150, y2=150)

    assert bbox_iou(left, right) == pytest.approx(2500 / 17500)


def test_tracker_keeps_stable_track_id_for_overlapping_person() -> None:
    tracker = ByteTrackTracker(ByteTrackConfig(match_threshold=0.3, track_ttl_frames=30))

    first = tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210))],
    )
    second = tracker.update(
        camera_id="camera-1",
        frame_sequence=2,
        detections=[make_detection(2, BoundingBox(14, 14, 114, 214))],
    )

    assert len(first) == 1
    assert len(second) == 1
    assert first[0].track_id == second[0].track_id
    assert second[0].hits == 2


def test_tracker_creates_new_track_for_distant_person() -> None:
    tracker = ByteTrackTracker(ByteTrackConfig(match_threshold=0.3, track_ttl_frames=30))

    first = tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210))],
    )
    second = tracker.update(
        camera_id="camera-1",
        frame_sequence=2,
        detections=[make_detection(2, BoundingBox(300, 10, 400, 210))],
    )

    assert first[0].track_id == 1
    assert second[0].track_id == 2


def test_tracker_state_is_isolated_per_camera() -> None:
    tracker = ByteTrackTracker(ByteTrackConfig(match_threshold=0.3, track_ttl_frames=30))

    camera_one = tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210), camera_id="camera-1")],
    )
    camera_two = tracker.update(
        camera_id="camera-2",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210), camera_id="camera-2")],
    )

    assert camera_one[0].camera_id == "camera-1"
    assert camera_two[0].camera_id == "camera-2"
    assert camera_one[0].track_id == 1
    assert camera_two[0].track_id == 1


def test_tracker_ignores_non_person_and_low_confidence_detections() -> None:
    tracker = ByteTrackTracker(ByteTrackConfig(new_track_threshold=0.5))

    tracked = tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[
            make_detection(1, BoundingBox(10, 10, 110, 210), confidence=0.49),
            make_detection(1, BoundingBox(20, 20, 120, 220), confidence=0.95, class_name="car"),
        ],
    )

    assert tracked == []
    assert tracker.metadata().active_tracks == 0


def test_tracker_expires_stale_tracks_after_ttl() -> None:
    tracker = ByteTrackTracker(ByteTrackConfig(track_ttl_frames=2))

    tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210))],
    )

    assert tracker.metadata().active_tracks == 1

    tracker.update(camera_id="camera-1", frame_sequence=3, detections=[])
    assert tracker.metadata().active_tracks == 1

    tracker.update(camera_id="camera-1", frame_sequence=4, detections=[])
    assert tracker.metadata().active_tracks == 0


def test_tracker_serializes_tracked_object() -> None:
    tracker = ByteTrackTracker()
    tracked = tracker.update(
        camera_id="camera-1",
        frame_sequence=1,
        detections=[make_detection(1, BoundingBox(10, 10, 110, 210), confidence=0.8)],
    )

    payload = tracked[0].as_dict()

    assert payload["camera_id"] == "camera-1"
    assert payload["track_id"] == 1
    assert payload["bbox"] == {
        "x1": 10,
        "y1": 10,
        "x2": 110,
        "y2": 210,
        "width": 100,
        "height": 200,
    }


def test_tracker_factory_builds_bytetrack_tracker() -> None:
    tracker = build_tracker(
        runtime="bytetrack",
        match_threshold=0.4,
        track_ttl_frames=12,
        new_track_threshold=0.7,
    )

    metadata = tracker.metadata().as_dict()
    assert metadata["runtime"] == "bytetrack"
    assert metadata["match_threshold"] == 0.4
    assert metadata["track_ttl_frames"] == 12
    assert metadata["new_track_threshold"] == 0.7


def test_tracker_factory_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported tracker runtime"):
        build_tracker(
            runtime="unknown",
            match_threshold=0.3,
            track_ttl_frames=30,
            new_track_threshold=0.5,
        )


def test_bytetrack_config_validates_thresholds() -> None:
    with pytest.raises(ValueError, match="match_threshold"):
        ByteTrackConfig(match_threshold=1.1)
    with pytest.raises(ValueError, match="track_ttl_frames"):
        ByteTrackConfig(track_ttl_frames=-1)
    with pytest.raises(ValueError, match="new_track_threshold"):
        ByteTrackConfig(new_track_threshold=-0.1)


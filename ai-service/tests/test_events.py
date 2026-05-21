from datetime import datetime, timedelta, timezone

from app.detection.schemas import BoundingBox
from app.events.engine import EventEngine
from app.events.publisher import InMemoryEventPublisher
from app.events.rules import bbox_centroid, point_in_polygon
from app.events.schemas import (
    EventRuleConfig,
    EventType,
    Point,
    RecognitionResult,
    RestrictedZone,
    VisionEvent,
)
from app.storage.snapshots import SnapshotStore
from app.tracking.schemas import TrackedObject
from app.video.source import VideoFrame
from app.video.status import CameraState, CameraStatus


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 5, 21, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


class FakeSnapshotStore(SnapshotStore):
    def __init__(self) -> None:
        self.saved_event_ids: list[str] = []

    def save(self, event: VisionEvent, frame: VideoFrame | None) -> str | None:
        self.saved_event_ids.append(event.event_id)
        return f"snapshots/{event.camera_id}/{event.event_id}.jpg"


def make_track(
    track_id: int = 1,
    frame_sequence: int = 1,
    bbox: BoundingBox | None = None,
    camera_id: str = "camera-1",
    confidence: float = 0.9,
) -> TrackedObject:
    return TrackedObject(
        camera_id=camera_id,
        frame_sequence=frame_sequence,
        timestamp=datetime(2026, 5, 21, tzinfo=timezone.utc),
        track_id=track_id,
        bbox=bbox or BoundingBox(x1=10, y1=10, x2=110, y2=210),
        class_id=0,
        class_name="person",
        confidence=confidence,
        hits=1,
    )


def make_engine(
    clock: FakeClock,
    restricted_zones: tuple[RestrictedZone, ...] = (),
) -> tuple[EventEngine, InMemoryEventPublisher, FakeSnapshotStore]:
    publisher = InMemoryEventPublisher()
    snapshots = FakeSnapshotStore()
    engine = EventEngine(
        config=EventRuleConfig(
            person_cooldown_seconds=60,
            known_person_cooldown_seconds=120,
            unknown_person_cooldown_seconds=120,
            restricted_zone_cooldown_seconds=300,
            camera_offline_cooldown_seconds=300,
            people_count_interval_seconds=10,
        ),
        restricted_zones=restricted_zones,
        snapshot_store=snapshots,
        publisher=publisher,
        clock=clock,
    )
    return engine, publisher, snapshots


def test_person_detected_and_people_count_events_are_published() -> None:
    clock = FakeClock()
    engine, publisher, snapshots = make_engine(clock)

    events = engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])

    assert [event.event_type for event in events] == [
        EventType.PERSON_DETECTED,
        EventType.PEOPLE_COUNT,
    ]
    assert events[0].metadata["track_id"] == 1
    assert events[1].metadata == {"count": 1, "track_ids": [1]}
    assert len(publisher.events) == 2
    assert len(snapshots.saved_event_ids) == 2
    assert events[0].snapshot_url is not None


def test_person_detected_is_deduplicated_by_track_until_cooldown_expires() -> None:
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock)

    first = engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])
    second = engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])

    assert [event.event_type for event in first] == [
        EventType.PERSON_DETECTED,
        EventType.PEOPLE_COUNT,
    ]
    assert second == []

    clock.advance(60)
    third = engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])

    assert [event.event_type for event in third] == [EventType.PERSON_DETECTED]


def test_people_count_event_emits_only_when_count_changes() -> None:
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock)

    engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track(track_id=1)])
    clock.advance(10)
    unchanged = engine.process_tracked_objects(
        camera_id="camera-1",
        tracked_objects=[make_track(track_id=1, frame_sequence=2)],
    )
    clock.advance(10)
    changed = engine.process_tracked_objects(
        camera_id="camera-1",
        tracked_objects=[
            make_track(track_id=1, frame_sequence=3),
            make_track(track_id=2, frame_sequence=3, bbox=BoundingBox(200, 10, 280, 210)),
        ],
    )

    assert unchanged == []
    assert [event.event_type for event in changed] == [
        EventType.PERSON_DETECTED,
        EventType.PEOPLE_COUNT,
    ]
    assert changed[-1].metadata["count"] == 2


def test_restricted_zone_entry_uses_bbox_centroid() -> None:
    zone = RestrictedZone(
        zone_id="zone-1",
        name="Door",
        polygon=(
            Point(0, 0),
            Point(150, 0),
            Point(150, 250),
            Point(0, 250),
        ),
    )
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock, restricted_zones=(zone,))

    events = engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])

    assert EventType.RESTRICTED_ZONE_ENTRY in [event.event_type for event in events]
    restricted_event = next(
        event for event in events if event.event_type == EventType.RESTRICTED_ZONE_ENTRY
    )
    assert restricted_event.metadata["zone_id"] == "zone-1"
    assert restricted_event.metadata["centroid"] == {"x": 60.0, "y": 110.0}


def test_point_in_polygon_helpers() -> None:
    polygon = (Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10))

    assert point_in_polygon(Point(5, 5), polygon) is True
    assert point_in_polygon(Point(15, 5), polygon) is False
    assert bbox_centroid(BoundingBox(0, 0, 10, 20)) == Point(5, 10)


def test_known_and_unknown_person_events_are_created_from_recognition_results() -> None:
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock)

    events = engine.process_tracked_objects(
        camera_id="camera-1",
        tracked_objects=[make_track(track_id=1), make_track(track_id=2)],
        recognition_results=[
            RecognitionResult(
                camera_id="camera-1",
                track_id=1,
                is_known=True,
                person_id="person-1",
                score=0.82,
                threshold=0.65,
                face_bbox=BoundingBox(20, 20, 60, 80),
            ),
            RecognitionResult(
                camera_id="camera-1",
                track_id=2,
                is_known=False,
                score=0.42,
                threshold=0.65,
            ),
        ],
    )

    event_types = [event.event_type for event in events]
    assert EventType.KNOWN_PERSON_DETECTED in event_types
    assert EventType.UNKNOWN_PERSON_DETECTED in event_types

    known = next(event for event in events if event.event_type == EventType.KNOWN_PERSON_DETECTED)
    unknown = next(event for event in events if event.event_type == EventType.UNKNOWN_PERSON_DETECTED)
    assert known.metadata["person_id"] == "person-1"
    assert known.metadata["face_bbox"] is not None
    assert unknown.metadata["person_id"] is None


def test_camera_offline_event_emits_once_per_offline_episode() -> None:
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock)
    status = CameraStatus(
        camera_id="camera-1",
        source_type="rtsp",
        source_uri="rtsp://example/stream",
        processing_fps=5,
    )
    status.mark_offline("read timeout")

    first = engine.process_camera_status(status)
    second = engine.process_camera_status(status)

    assert [event.event_type for event in first] == [EventType.CAMERA_OFFLINE]
    assert first[0].metadata["error"] == "read timeout"
    assert second == []

    status.mark_online()
    assert engine.process_camera_status(status) == []
    status.mark_offline("read timeout")
    clock.advance(300)

    third = engine.process_camera_status(status)
    assert [event.event_type for event in third] == [EventType.CAMERA_OFFLINE]


def test_event_metadata_reports_engine_state() -> None:
    clock = FakeClock()
    engine, _publisher, _snapshots = make_engine(clock)

    engine.process_tracked_objects(camera_id="camera-1", tracked_objects=[make_track()])
    metadata = engine.metadata().as_dict()

    assert metadata["pending_published_events"] == 2
    assert metadata["cooldown_keys"] == 2
    assert metadata["restricted_zones"] == 0


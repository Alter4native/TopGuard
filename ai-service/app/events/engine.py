from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from app.events.publisher import EventPublisher, InMemoryEventPublisher
from app.events.rules import bbox_centroid, containing_zones
from app.events.schemas import (
    EventRuleConfig,
    EventType,
    RecognitionResult,
    RestrictedZone,
    VisionEvent,
)
from app.storage.snapshots import NoopSnapshotStore, SnapshotStore
from app.tracking.schemas import TrackedObject
from app.video.source import VideoFrame
from app.video.status import CameraState, CameraStatus


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EventEngineMetadata:
    pending_published_events: int
    cooldown_keys: int
    restricted_zones: int

    def as_dict(self) -> dict[str, int]:
        return {
            "pending_published_events": self.pending_published_events,
            "cooldown_keys": self.cooldown_keys,
            "restricted_zones": self.restricted_zones,
        }


class EventEngine:
    def __init__(
        self,
        config: EventRuleConfig | None = None,
        restricted_zones: Sequence[RestrictedZone] | None = None,
        snapshot_store: SnapshotStore | None = None,
        publisher: EventPublisher | None = None,
        clock: Clock = utc_now,
    ) -> None:
        self.config = config or EventRuleConfig()
        self.restricted_zones = tuple(restricted_zones or ())
        self.snapshot_store = snapshot_store or NoopSnapshotStore()
        self.publisher = publisher or InMemoryEventPublisher()
        self.clock = clock
        self._last_event_at: dict[tuple[str, EventType, str], datetime] = {}
        self._last_people_count: dict[str, int] = {}
        self._offline_episode_emitted: set[str] = set()

    def process_tracked_objects(
        self,
        camera_id: str,
        tracked_objects: Sequence[TrackedObject],
        frame: VideoFrame | None = None,
        recognition_results: Sequence[RecognitionResult] | None = None,
    ) -> list[VisionEvent]:
        now = self.clock()
        events: list[VisionEvent] = []
        recognition_by_track = {
            result.track_id: result for result in recognition_results or [] if result.camera_id == camera_id
        }

        for tracked_object in tracked_objects:
            person_event = self._person_detected_event(camera_id, tracked_object, now)
            if person_event is not None:
                events.append(person_event)

            recognition = recognition_by_track.get(tracked_object.track_id)
            if recognition is not None:
                recognition_event = self._recognition_event(tracked_object, recognition, now)
                if recognition_event is not None:
                    events.append(recognition_event)

            events.extend(self._restricted_zone_events(camera_id, tracked_object, now))

        count_event = self._people_count_event(camera_id, tracked_objects, now)
        if count_event is not None:
            events.append(count_event)

        self._attach_snapshots(events, frame)
        self.publisher.publish(events)
        return events

    def process_camera_status(self, status: CameraStatus) -> list[VisionEvent]:
        now = self.clock()

        if status.state == CameraState.ONLINE:
            self._offline_episode_emitted.discard(status.camera_id)
            return []

        if status.state != CameraState.OFFLINE:
            return []

        if status.camera_id in self._offline_episode_emitted:
            return []

        if not self._allow_event(
            camera_id=status.camera_id,
            event_type=EventType.CAMERA_OFFLINE,
            dedup_key="offline",
            now=now,
        ):
            return []

        self._offline_episode_emitted.add(status.camera_id)
        event = VisionEvent(
            camera_id=status.camera_id,
            event_type=EventType.CAMERA_OFFLINE,
            confidence=1.0,
            timestamp=now,
            metadata={
                "last_frame_at": status.last_frame_at.isoformat() if status.last_frame_at else None,
                "error": status.last_error,
                "reconnect_attempts": status.reconnect_attempts,
            },
        )
        self.publisher.publish([event])
        return [event]

    def metadata(self) -> EventEngineMetadata:
        published = getattr(self.publisher, "events", [])
        return EventEngineMetadata(
            pending_published_events=len(published),
            cooldown_keys=len(self._last_event_at),
            restricted_zones=len(self.restricted_zones),
        )

    def _person_detected_event(
        self,
        camera_id: str,
        tracked_object: TrackedObject,
        now: datetime,
    ) -> VisionEvent | None:
        dedup_key = str(tracked_object.track_id)
        if not self._allow_event(camera_id, EventType.PERSON_DETECTED, dedup_key, now):
            return None

        return VisionEvent(
            camera_id=camera_id,
            event_type=EventType.PERSON_DETECTED,
            confidence=tracked_object.confidence,
            timestamp=now,
            metadata={
                "track_id": tracked_object.track_id,
                "frame_sequence": tracked_object.frame_sequence,
                "bbox": tracked_object.bbox.as_dict(),
                "class_name": tracked_object.class_name,
            },
        )

    def _recognition_event(
        self,
        tracked_object: TrackedObject,
        recognition: RecognitionResult,
        now: datetime,
    ) -> VisionEvent | None:
        if recognition.is_known and recognition.person_id:
            event_type = EventType.KNOWN_PERSON_DETECTED
            dedup_key = f"{tracked_object.track_id}:{recognition.person_id}"
        else:
            event_type = EventType.UNKNOWN_PERSON_DETECTED
            dedup_key = str(tracked_object.track_id)

        if not self._allow_event(tracked_object.camera_id, event_type, dedup_key, now):
            return None

        metadata = {
            "track_id": tracked_object.track_id,
            "person_id": recognition.person_id,
            "recognition_score": recognition.score,
            "recognition_threshold": recognition.threshold,
            "bbox": tracked_object.bbox.as_dict(),
            "face_bbox": recognition.face_bbox.as_dict() if recognition.face_bbox else None,
        }

        return VisionEvent(
            camera_id=tracked_object.camera_id,
            event_type=event_type,
            confidence=recognition.score,
            timestamp=now,
            metadata=metadata,
        )

    def _restricted_zone_events(
        self,
        camera_id: str,
        tracked_object: TrackedObject,
        now: datetime,
    ) -> list[VisionEvent]:
        events: list[VisionEvent] = []
        centroid = bbox_centroid(tracked_object.bbox)

        for zone in containing_zones(tracked_object.bbox, self.restricted_zones):
            dedup_key = f"{tracked_object.track_id}:{zone.zone_id}"
            if not self._allow_event(camera_id, EventType.RESTRICTED_ZONE_ENTRY, dedup_key, now):
                continue

            events.append(
                VisionEvent(
                    camera_id=camera_id,
                    event_type=EventType.RESTRICTED_ZONE_ENTRY,
                    confidence=tracked_object.confidence,
                    timestamp=now,
                    metadata={
                        "track_id": tracked_object.track_id,
                        "zone_id": zone.zone_id,
                        "zone_name": zone.name,
                        "bbox": tracked_object.bbox.as_dict(),
                        "centroid": centroid.as_dict(),
                    },
                )
            )

        return events

    def _people_count_event(
        self,
        camera_id: str,
        tracked_objects: Sequence[TrackedObject],
        now: datetime,
    ) -> VisionEvent | None:
        track_ids = sorted({tracked_object.track_id for tracked_object in tracked_objects})
        count = len(track_ids)
        previous_count = self._last_people_count.get(camera_id)
        if previous_count == count:
            return None

        if not self._allow_event(camera_id, EventType.PEOPLE_COUNT, "count", now):
            return None

        self._last_people_count[camera_id] = count
        return VisionEvent(
            camera_id=camera_id,
            event_type=EventType.PEOPLE_COUNT,
            confidence=1.0,
            timestamp=now,
            metadata={"count": count, "track_ids": track_ids},
        )

    def _attach_snapshots(self, events: Sequence[VisionEvent], frame: VideoFrame | None) -> None:
        for event in events:
            snapshot_url = self.snapshot_store.save(event, frame)
            event.with_snapshot(snapshot_url)

    def _allow_event(
        self,
        camera_id: str,
        event_type: EventType,
        dedup_key: str,
        now: datetime,
    ) -> bool:
        key = (camera_id, event_type, dedup_key)
        last_seen_at = self._last_event_at.get(key)
        cooldown_seconds = self.config.cooldown_for(event_type)

        if last_seen_at is not None and (now - last_seen_at).total_seconds() < cooldown_seconds:
            return False

        self._last_event_at[key] = now
        return True


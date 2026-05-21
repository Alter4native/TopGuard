from pathlib import Path

from app.events.schemas import VisionEvent
from app.video.source import VideoFrame


class SnapshotStore:
    def save(self, event: VisionEvent, frame: VideoFrame | None) -> str | None:
        raise NotImplementedError


class NoopSnapshotStore(SnapshotStore):
    def save(self, event: VisionEvent, frame: VideoFrame | None) -> str | None:
        return None


class LocalSnapshotStore(SnapshotStore):
    def __init__(self, root_path: str) -> None:
        self.root_path = Path(root_path)

    def save(self, event: VisionEvent, frame: VideoFrame | None) -> str | None:
        if frame is None or frame.image is None:
            return None

        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("OpenCV is required to save snapshots") from exc

        day_path = event.timestamp.strftime("%Y/%m/%d")
        relative_path = Path(event.camera_id) / day_path / f"{event.event_id}.jpg"
        output_path = self.root_path / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ok = cv2.imwrite(str(output_path), frame.image)
        if not ok:
            raise RuntimeError(f"Unable to write snapshot: {output_path}")

        return relative_path.as_posix()


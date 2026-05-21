from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CameraState(StrEnum):
    STOPPED = "stopped"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class CameraStatus:
    camera_id: str
    source_type: str
    source_uri: str
    processing_fps: int
    state: CameraState = CameraState.STOPPED
    last_frame_at: datetime | None = None
    last_error: str | None = None
    frames_read: int = 0
    reconnect_attempts: int = 0
    updated_at: datetime = field(default_factory=utc_now)

    def mark_online(self) -> None:
        self.state = CameraState.ONLINE
        self.last_error = None
        self.updated_at = utc_now()

    def mark_frame(self) -> None:
        self.frames_read += 1
        self.last_frame_at = utc_now()
        self.mark_online()

    def mark_offline(self, error: str | None = None) -> None:
        self.state = CameraState.OFFLINE
        self.last_error = error
        self.updated_at = utc_now()

    def mark_error(self, error: str) -> None:
        self.state = CameraState.ERROR
        self.last_error = error
        self.updated_at = utc_now()

    def mark_reconnect_attempt(self) -> None:
        self.reconnect_attempts += 1
        self.updated_at = utc_now()

    def as_dict(self) -> dict[str, object]:
        return {
            "camera_id": self.camera_id,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "processing_fps": self.processing_fps,
            "state": self.state.value,
            "last_frame_at": self.last_frame_at.isoformat() if self.last_frame_at else None,
            "last_error": self.last_error,
            "frames_read": self.frames_read,
            "reconnect_attempts": self.reconnect_attempts,
            "updated_at": self.updated_at.isoformat(),
        }


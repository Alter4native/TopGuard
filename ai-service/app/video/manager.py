import time
from dataclasses import dataclass
from typing import Callable

from app.video.rtsp import RTSPCameraSource
from app.video.sampler import FrameSampler
from app.video.source import CameraOpenError, CameraReadError, CameraSource, VideoFrame
from app.video.status import CameraStatus
from app.video.webcam import WebcamCameraSource


@dataclass(frozen=True)
class CameraConfig:
    camera_id: str
    source_type: str
    source_uri: str
    processing_fps: int
    reconnect_backoff_seconds: float = 1.0
    max_reconnect_backoff_seconds: float = 30.0
    open_timeout_ms: int = 5000
    read_timeout_ms: int = 5000


SourceFactory = Callable[[CameraConfig], CameraSource]
Clock = Callable[[], float]


def build_camera_source(config: CameraConfig) -> CameraSource:
    source_type = config.source_type.lower()
    if source_type == "webcam":
        return WebcamCameraSource(
            camera_id=config.camera_id,
            uri=config.source_uri,
            open_timeout_ms=config.open_timeout_ms,
            read_timeout_ms=config.read_timeout_ms,
        )
    if source_type == "rtsp":
        return RTSPCameraSource(
            camera_id=config.camera_id,
            uri=config.source_uri,
            open_timeout_ms=config.open_timeout_ms,
            read_timeout_ms=config.read_timeout_ms,
        )

    raise CameraOpenError(f"Unsupported camera source type: {config.source_type}")


class CameraManager:
    def __init__(
        self,
        config: CameraConfig,
        source_factory: SourceFactory = build_camera_source,
        clock: Clock = time.monotonic,
    ) -> None:
        self.config = config
        self._source_factory = source_factory
        self._clock = clock
        self._source: CameraSource | None = None
        self._sampler = FrameSampler(config.processing_fps)
        self._next_reconnect_at = 0.0
        self._current_backoff = config.reconnect_backoff_seconds
        self.status = CameraStatus(
            camera_id=config.camera_id,
            source_type=config.source_type,
            source_uri=config.source_uri,
            processing_fps=config.processing_fps,
        )

    def read_next(self) -> VideoFrame | None:
        now = self._clock()
        if not self._sampler.should_process(now):
            return None

        if not self._ensure_open(now):
            return None

        assert self._source is not None
        try:
            frame = self._source.read()
        except CameraReadError as exc:
            self.status.mark_offline(str(exc))
            self._schedule_reconnect(now)
            self._close_source()
            return None

        self.status.mark_frame()
        return frame

    def close(self) -> None:
        self._close_source()

    def get_status(self) -> dict[str, object]:
        return self.status.as_dict()

    def _ensure_open(self, now: float) -> bool:
        if self._source is not None and self._source.is_open():
            return True

        if now < self._next_reconnect_at:
            return False

        try:
            self.status.mark_reconnect_attempt()
            self._source = self._source_factory(self.config)
            self._source.open()
        except CameraOpenError as exc:
            self.status.mark_offline(str(exc))
            self._schedule_reconnect(now)
            self._close_source()
            return False

        self.status.mark_online()
        self._current_backoff = self.config.reconnect_backoff_seconds
        self._next_reconnect_at = now
        return True

    def _schedule_reconnect(self, now: float) -> None:
        self._next_reconnect_at = now + self._current_backoff
        self._current_backoff = min(
            self._current_backoff * 2,
            self.config.max_reconnect_backoff_seconds,
        )

    def _close_source(self) -> None:
        if self._source is not None:
            self._source.close()
        self._source = None

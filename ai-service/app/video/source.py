from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


class CameraSourceError(RuntimeError):
    pass


class CameraOpenError(CameraSourceError):
    pass


class CameraReadError(CameraSourceError):
    pass


@dataclass(frozen=True)
class VideoFrame:
    camera_id: str
    sequence: int
    timestamp: datetime
    image: Any
    width: int | None = None
    height: int | None = None


class CameraSource(ABC):
    def __init__(self, camera_id: str, uri: str) -> None:
        self.camera_id = camera_id
        self.uri = uri
        self._sequence = 0

    @abstractmethod
    def open(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> VideoFrame:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    def _next_frame(self, image: Any) -> VideoFrame:
        self._sequence += 1
        height: int | None = None
        width: int | None = None

        shape = getattr(image, "shape", None)
        if shape is not None and len(shape) >= 2:
            height = int(shape[0])
            width = int(shape[1])

        return VideoFrame(
            camera_id=self.camera_id,
            sequence=self._sequence,
            timestamp=datetime.now(timezone.utc),
            image=image,
            width=width,
            height=height,
        )


class OpenCVCameraSource(CameraSource):
    def __init__(
        self,
        camera_id: str,
        uri: str | int,
        open_timeout_ms: int = 5000,
        read_timeout_ms: int = 5000,
    ) -> None:
        super().__init__(camera_id=camera_id, uri=str(uri))
        self.capture_uri = uri
        self._capture: Any = None
        self.open_timeout_ms = open_timeout_ms
        self.read_timeout_ms = read_timeout_ms

    def open(self) -> None:
        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CameraOpenError("OpenCV is not installed") from exc

        self._capture = cv2.VideoCapture()
        self._set_timeout(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC", self.open_timeout_ms)
        self._set_timeout(cv2, "CAP_PROP_READ_TIMEOUT_MSEC", self.read_timeout_ms)

        opened = self._capture.open(self.capture_uri)
        if not opened or not self._capture.isOpened():
            self.close()
            raise CameraOpenError(f"Unable to open camera source: {self.uri}")

    def read(self) -> VideoFrame:
        if not self._capture or not self._capture.isOpened():
            raise CameraReadError("Camera source is not open")

        ok, image = self._capture.read()
        if not ok or image is None:
            raise CameraReadError(f"Unable to read frame from camera source: {self.uri}")

        return self._next_frame(image)

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None

    def is_open(self) -> bool:
        return bool(self._capture is not None and self._capture.isOpened())

    def _set_timeout(self, cv2: Any, property_name: str, value: int) -> None:
        property_id = getattr(cv2, property_name, None)
        if property_id is not None and self._capture is not None:
            self._capture.set(property_id, value)


class MockCameraSource(CameraSource):
    def __init__(
        self,
        camera_id: str,
        frames: Iterable[Any],
        fail_open: bool = False,
        fail_after_reads: int | None = None,
    ) -> None:
        super().__init__(camera_id=camera_id, uri="mock")
        self._frames = list(frames)
        self._opened = False
        self._read_index = 0
        self._fail_open = fail_open
        self._fail_after_reads = fail_after_reads

    def open(self) -> None:
        if self._fail_open:
            raise CameraOpenError("Mock source failed to open")
        self._opened = True

    def read(self) -> VideoFrame:
        if not self._opened:
            raise CameraReadError("Mock source is not open")
        if self._fail_after_reads is not None and self._read_index >= self._fail_after_reads:
            raise CameraReadError("Mock source read failure")
        if self._read_index >= len(self._frames):
            raise CameraReadError("Mock source has no more frames")

        frame = self._next_frame(self._frames[self._read_index])
        self._read_index += 1
        return frame

    def close(self) -> None:
        self._opened = False

    def is_open(self) -> bool:
        return self._opened

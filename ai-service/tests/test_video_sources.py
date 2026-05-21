from dataclasses import dataclass

import pytest

from app.video.manager import CameraConfig, CameraManager, build_camera_source
from app.video.rtsp import RTSPCameraSource
from app.video.sampler import FrameSampler
from app.video.source import CameraOpenError, MockCameraSource
from app.video.status import CameraState
from app.video.webcam import WebcamCameraSource, parse_webcam_uri


@dataclass
class FakeImage:
    shape: tuple[int, int, int] = (10, 20, 3)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_config(processing_fps: int = 5) -> CameraConfig:
    return CameraConfig(
        camera_id="camera-1",
        source_type="webcam",
        source_uri="0",
        processing_fps=processing_fps,
        reconnect_backoff_seconds=1.0,
        max_reconnect_backoff_seconds=4.0,
    )


def test_frame_sampler_limits_processing_rate() -> None:
    sampler = FrameSampler(processing_fps=5)

    assert sampler.should_process(0.0) is True
    assert sampler.should_process(0.1) is False
    assert sampler.should_process(0.2) is True
    assert sampler.should_process(0.3) is False
    assert sampler.should_process(0.4) is True


def test_frame_sampler_rejects_invalid_fps() -> None:
    with pytest.raises(ValueError, match="processing_fps"):
        FrameSampler(processing_fps=0)


def test_webcam_uri_parses_numeric_index() -> None:
    assert parse_webcam_uri("0") == 0
    assert parse_webcam_uri("1") == 1
    assert parse_webcam_uri("video.mp4") == "video.mp4"


def test_source_factory_creates_webcam_and_rtsp_sources() -> None:
    webcam = build_camera_source(make_config())
    assert isinstance(webcam, WebcamCameraSource)

    rtsp = build_camera_source(
        CameraConfig(
            camera_id="camera-1",
            source_type="rtsp",
            source_uri="rtsp://example.local/stream",
            processing_fps=5,
        )
    )
    assert isinstance(rtsp, RTSPCameraSource)


def test_source_factory_rejects_invalid_rtsp_uri() -> None:
    with pytest.raises(CameraOpenError, match="rtsp://"):
        build_camera_source(
            CameraConfig(
                camera_id="camera-1",
                source_type="rtsp",
                source_uri="http://example.local/stream",
                processing_fps=5,
            )
        )


def test_camera_manager_reads_frames_and_updates_status() -> None:
    clock = FakeClock()
    source = MockCameraSource(camera_id="camera-1", frames=[FakeImage(), FakeImage()])
    manager = CameraManager(make_config(), source_factory=lambda _config: source, clock=clock)

    first_frame = manager.read_next()
    assert first_frame is not None
    assert first_frame.sequence == 1
    assert first_frame.width == 20
    assert first_frame.height == 10

    assert manager.read_next() is None

    clock.advance(0.2)
    second_frame = manager.read_next()
    assert second_frame is not None
    assert second_frame.sequence == 2

    status = manager.get_status()
    assert status["state"] == CameraState.ONLINE.value
    assert status["frames_read"] == 2
    assert status["reconnect_attempts"] == 1
    assert status["last_error"] is None


def test_camera_manager_marks_offline_when_open_fails() -> None:
    clock = FakeClock()

    def source_factory(_config: CameraConfig) -> MockCameraSource:
        return MockCameraSource(camera_id="camera-1", frames=[], fail_open=True)

    manager = CameraManager(make_config(), source_factory=source_factory, clock=clock)

    assert manager.read_next() is None
    status = manager.get_status()
    assert status["state"] == CameraState.OFFLINE.value
    assert status["reconnect_attempts"] == 1
    assert "failed to open" in str(status["last_error"])

    clock.advance(0.2)
    assert manager.read_next() is None
    assert manager.get_status()["reconnect_attempts"] == 1

    clock.advance(0.8)
    assert manager.read_next() is None
    assert manager.get_status()["reconnect_attempts"] == 2


def test_camera_manager_marks_offline_when_read_fails() -> None:
    clock = FakeClock()
    source = MockCameraSource(camera_id="camera-1", frames=[FakeImage()], fail_after_reads=1)
    manager = CameraManager(make_config(), source_factory=lambda _config: source, clock=clock)

    assert manager.read_next() is not None
    clock.advance(0.2)

    assert manager.read_next() is None
    status = manager.get_status()
    assert status["state"] == CameraState.OFFLINE.value
    assert status["frames_read"] == 1
    assert "read failure" in str(status["last_error"])


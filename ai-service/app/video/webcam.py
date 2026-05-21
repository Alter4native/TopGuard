from app.video.source import OpenCVCameraSource


def parse_webcam_uri(uri: str) -> int | str:
    return int(uri) if uri.isdigit() else uri


class WebcamCameraSource(OpenCVCameraSource):
    def __init__(
        self,
        camera_id: str,
        uri: str = "0",
        open_timeout_ms: int = 5000,
        read_timeout_ms: int = 5000,
    ) -> None:
        super().__init__(
            camera_id=camera_id,
            uri=parse_webcam_uri(uri),
            open_timeout_ms=open_timeout_ms,
            read_timeout_ms=read_timeout_ms,
        )

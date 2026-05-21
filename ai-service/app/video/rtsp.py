from app.video.source import CameraOpenError, OpenCVCameraSource


class RTSPCameraSource(OpenCVCameraSource):
    def __init__(
        self,
        camera_id: str,
        uri: str,
        open_timeout_ms: int = 5000,
        read_timeout_ms: int = 5000,
    ) -> None:
        if not uri.lower().startswith("rtsp://"):
            raise CameraOpenError("RTSP camera URI must start with rtsp://")
        super().__init__(
            camera_id=camera_id,
            uri=uri,
            open_timeout_ms=open_timeout_ms,
            read_timeout_ms=read_timeout_ms,
        )

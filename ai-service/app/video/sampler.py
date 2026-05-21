class FrameSampler:
    def __init__(self, processing_fps: int) -> None:
        if processing_fps <= 0:
            raise ValueError("processing_fps must be greater than 0")

        self.processing_fps = processing_fps
        self.interval_seconds = 1.0 / processing_fps
        self._last_emit_at: float | None = None

    def should_process(self, now: float) -> bool:
        if self._last_emit_at is None:
            self._last_emit_at = now
            return True

        if now - self._last_emit_at >= self.interval_seconds:
            self._last_emit_at = now
            return True

        return False

    def reset(self) -> None:
        self._last_emit_at = None


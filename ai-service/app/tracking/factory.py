from app.tracking.base import ObjectTracker
from app.tracking.bytetrack import ByteTrackConfig, ByteTrackTracker


def build_tracker(
    runtime: str,
    match_threshold: float,
    track_ttl_frames: int,
    new_track_threshold: float,
) -> ObjectTracker:
    normalized_runtime = runtime.lower()
    if normalized_runtime == "bytetrack":
        return ByteTrackTracker(
            ByteTrackConfig(
                match_threshold=match_threshold,
                track_ttl_frames=track_ttl_frames,
                new_track_threshold=new_track_threshold,
            )
        )

    raise ValueError(f"Unsupported tracker runtime: {runtime}")


from app.detection.base import ObjectDetector
from app.detection.yolo import YoloDetector


def build_detector(
    runtime: str,
    model_path: str,
    confidence_threshold: float,
) -> ObjectDetector:
    normalized_runtime = runtime.lower()
    if normalized_runtime == "yolo":
        return YoloDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            allowed_class_names=("person",),
        )

    raise ValueError(f"Unsupported detector runtime: {runtime}")


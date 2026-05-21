"""Recognition package."""

from app.recognition.base import EmbeddingStore, FaceRecognizer
from app.recognition.schemas import FaceRecognitionOutput, RecognitionDecision

__all__ = ["EmbeddingStore", "FaceRecognitionOutput", "FaceRecognizer", "RecognitionDecision"]


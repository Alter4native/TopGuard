import hashlib
from typing import Any

from app.detection.schemas import BoundingBox
from app.recognition.base import EmbeddingStore, FaceRecognizer
from app.recognition.schemas import (
    FaceEmbedding,
    FaceMatch,
    FaceRecognitionInput,
    FaceRecognitionOutput,
    FaceRecognizerMetadata,
    PersonEmbedding,
    RecognitionDecision,
)
from app.recognition.vector_store import InMemoryEmbeddingStore


class SimpleFaceRecognizer(FaceRecognizer):
    """Deterministic embedding recognizer for MVP wiring and tests.

    This is not a production biometric model. It provides the same contracts
    that the InsightFace/ONNX adapter will use, while keeping local tests fast
    and independent of model downloads.
    """

    def __init__(
        self,
        threshold: float = 0.65,
        embedding_dim: int = 32,
        model_name: str = "simple-hash-face-embedding",
        store: EmbeddingStore | None = None,
    ) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be greater than 0")

        self.threshold = threshold
        self.embedding_dim = embedding_dim
        self.model_name = model_name
        self.store = store or InMemoryEmbeddingStore()

    def enroll(
        self,
        person_id: str,
        image: object,
        face_bbox: BoundingBox,
        photo_id: str | None = None,
    ) -> PersonEmbedding:
        embedding = PersonEmbedding(
            person_id=person_id,
            photo_id=photo_id,
            embedding=self.embed(image=image, face_bbox=face_bbox),
        )
        self.store.upsert(embedding)
        return embedding

    def recognize(self, payload: FaceRecognitionInput) -> FaceRecognitionOutput | None:
        if payload.face_bbox is None:
            return None

        embedding = self.embed(image=payload.image, face_bbox=payload.face_bbox)
        match = self.match(embedding)

        return FaceRecognitionOutput(
            camera_id=payload.camera_id,
            track_id=payload.track_id,
            decision=match.decision,
            score=match.score,
            threshold=match.threshold,
            person_id=match.person_id,
            face_bbox=payload.face_bbox,
        )

    def metadata(self) -> FaceRecognizerMetadata:
        return FaceRecognizerMetadata(
            runtime="simple",
            model_name=self.model_name,
            embedding_dim=self.embedding_dim,
            threshold=self.threshold,
            enrolled_embeddings=self.store.count(),
            embedding_store=self.store.metadata(),
            person_reid_enabled=False,
        )

    def embed(self, image: object, face_bbox: BoundingBox) -> FaceEmbedding:
        digest_source = self._image_bytes(image) + repr(face_bbox.as_xyxy()).encode("utf-8")
        digest = hashlib.sha512(digest_source).digest()
        values: list[float] = []

        while len(values) < self.embedding_dim:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) == self.embedding_dim:
                    break
            digest = hashlib.sha512(digest).digest()

        return FaceEmbedding(
            vector=tuple(values),
            model_name=self.model_name,
            embedding_dim=self.embedding_dim,
        )

    def match(self, embedding: FaceEmbedding) -> FaceMatch:
        matches = self.store.search(embedding, limit=1)
        if not matches:
            return FaceMatch(
                person_id=None,
                score=0.0,
                threshold=self.threshold,
                decision=RecognitionDecision.UNKNOWN,
            )

        best_embedding, score = matches[0]
        if score >= self.threshold:
            return FaceMatch(
                person_id=best_embedding.person_id,
                score=score,
                threshold=self.threshold,
                decision=RecognitionDecision.KNOWN,
            )

        return FaceMatch(
            person_id=None,
            score=score,
            threshold=self.threshold,
            decision=RecognitionDecision.UNKNOWN,
        )

    def _image_bytes(self, image: Any) -> bytes:
        if isinstance(image, bytes):
            return image
        if isinstance(image, str):
            return image.encode("utf-8")
        if hasattr(image, "tobytes"):
            return image.tobytes()
        return repr(image).encode("utf-8")


class InsightFaceRecognizer(FaceRecognizer):
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError(
            "InsightFaceRecognizer is reserved for production model integration. "
            "Use SimpleFaceRecognizer for MVP tests or add insightface/onnxruntime in deployment."
        )

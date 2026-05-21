from abc import ABC, abstractmethod

from app.detection.schemas import BoundingBox
from app.recognition.schemas import (
    EmbeddingStoreMetadata,
    FaceEmbedding,
    FaceRecognitionInput,
    FaceRecognitionOutput,
    FaceRecognizerMetadata,
    PersonEmbedding,
)


class FaceRecognizer(ABC):
    @abstractmethod
    def enroll(
        self,
        person_id: str,
        image: object,
        face_bbox: BoundingBox,
        photo_id: str | None = None,
    ) -> PersonEmbedding:
        raise NotImplementedError

    @abstractmethod
    def recognize(self, payload: FaceRecognitionInput) -> FaceRecognitionOutput | None:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> FaceRecognizerMetadata:
        raise NotImplementedError


class EmbeddingStore(ABC):
    @abstractmethod
    def upsert(self, embedding: PersonEmbedding) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, embedding: FaceEmbedding, limit: int = 1) -> list[tuple[PersonEmbedding, float]]:
        raise NotImplementedError

    @abstractmethod
    def delete_person(self, person_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> EmbeddingStoreMetadata:
        raise NotImplementedError

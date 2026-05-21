from math import sqrt
from uuid import NAMESPACE_URL, uuid5

from app.recognition.base import EmbeddingStore
from app.recognition.schemas import EmbeddingStoreMetadata, FaceEmbedding, PersonEmbedding

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:  # pragma: no cover - exercised only in stripped runtime images.
    QdrantClient = None
    models = None


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions must match")

    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return dot / (left_norm * right_norm)


class InMemoryEmbeddingStore(EmbeddingStore):
    def __init__(self) -> None:
        self._embeddings: list[PersonEmbedding] = []

    def upsert(self, embedding: PersonEmbedding) -> None:
        self._embeddings = [
            existing
            for existing in self._embeddings
            if not (
                existing.person_id == embedding.person_id
                and existing.photo_id == embedding.photo_id
                and existing.embedding.model_name == embedding.embedding.model_name
            )
        ]
        self._embeddings.append(embedding)

    def search(self, embedding: FaceEmbedding, limit: int = 1) -> list[tuple[PersonEmbedding, float]]:
        matches = [
            (existing, cosine_similarity(existing.embedding.vector, embedding.vector))
            for existing in self._embeddings
            if existing.embedding.embedding_dim == embedding.embedding_dim
        ]
        matches.sort(key=lambda item: item[1], reverse=True)
        return matches[:limit]

    def delete_person(self, person_id: str) -> int:
        before = len(self._embeddings)
        self._embeddings = [embedding for embedding in self._embeddings if embedding.person_id != person_id]
        return before - len(self._embeddings)

    def count(self) -> int:
        return len(self._embeddings)

    def metadata(self) -> EmbeddingStoreMetadata:
        return EmbeddingStoreMetadata(
            runtime="memory",
            collection=None,
            status="ready",
        )


class QdrantEmbeddingStore(EmbeddingStore):
    def __init__(
        self,
        url: str,
        collection_name: str,
        embedding_dim: int,
        api_key: str | None = None,
        timeout_seconds: int = 3,
        client: object | None = None,
    ) -> None:
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be greater than 0")
        if client is None and QdrantClient is None:
            raise RuntimeError("qdrant-client is required for QdrantEmbeddingStore")

        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._client = client or self._create_client(url, api_key, timeout_seconds)
        self._ready = False
        self._last_error: str | None = None

    def upsert(self, embedding: PersonEmbedding) -> None:
        self._ensure_collection()
        if embedding.embedding.embedding_dim != self.embedding_dim:
            raise ValueError("Embedding dimension does not match Qdrant collection dimension")

        point_id = self._point_id(embedding)
        self._client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=list(embedding.embedding.vector),
                    payload={
                        "person_id": embedding.person_id,
                        "photo_id": embedding.photo_id,
                        "model_name": embedding.embedding.model_name,
                        "embedding_dim": embedding.embedding.embedding_dim,
                        "created_at": embedding.created_at.isoformat(),
                    },
                )
            ],
            wait=True,
        )

    def search(self, embedding: FaceEmbedding, limit: int = 1) -> list[tuple[PersonEmbedding, float]]:
        self._ensure_collection()
        if embedding.embedding_dim != self.embedding_dim:
            raise ValueError("Embedding dimension does not match Qdrant collection dimension")

        scored_points = self._client.search(
            collection_name=self.collection_name,
            query_vector=list(embedding.vector),
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )
        matches: list[tuple[PersonEmbedding, float]] = []
        for point in scored_points:
            payload = point.payload or {}
            person_id = payload.get("person_id")
            if not isinstance(person_id, str):
                continue

            point_vector = self._point_vector(point.vector, embedding.embedding_dim)
            stored_embedding = PersonEmbedding(
                person_id=person_id,
                photo_id=payload.get("photo_id") if isinstance(payload.get("photo_id"), str) else None,
                embedding=FaceEmbedding(
                    vector=point_vector,
                    model_name=str(payload.get("model_name") or embedding.model_name),
                    embedding_dim=embedding.embedding_dim,
                ),
            )
            matches.append((stored_embedding, float(point.score)))

        return matches

    def delete_person(self, person_id: str) -> int:
        self._ensure_collection()
        result = self._client.delete(
            collection_name=self.collection_name,
            points_selector=models.Filter(
                must=[
                    models.FieldCondition(
                        key="person_id",
                        match=models.MatchValue(value=person_id),
                    )
                ]
            ),
            wait=True,
        )
        return int(getattr(result, "operation_id", 0) or 0)

    def count(self) -> int:
        try:
            self._ensure_collection()
            return int(self._client.count(collection_name=self.collection_name, exact=True).count)
        except Exception as exc:  # pragma: no cover - depends on external Qdrant availability.
            self._ready = False
            self._last_error = str(exc)
            return 0

    def metadata(self) -> EmbeddingStoreMetadata:
        return EmbeddingStoreMetadata(
            runtime="qdrant",
            collection=self.collection_name,
            status="ready" if self._ready else "unavailable",
            last_error=self._last_error,
        )

    def _ensure_collection(self) -> None:
        try:
            if not self._client.collection_exists(self.collection_name):
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=self.embedding_dim, distance=models.Distance.COSINE),
                )
            else:
                info = self._client.get_collection(self.collection_name)
                vector_params = info.config.params.vectors
                if getattr(vector_params, "size", self.embedding_dim) != self.embedding_dim:
                    raise ValueError("Existing Qdrant collection has a different vector dimension")
            self._ready = True
            self._last_error = None
        except Exception as exc:
            self._ready = False
            self._last_error = str(exc)
            raise

    def _point_id(self, embedding: PersonEmbedding) -> str:
        photo_key = embedding.photo_id or "no-photo"
        raw = f"{embedding.person_id}:{photo_key}:{embedding.embedding.model_name}"
        return str(uuid5(NAMESPACE_URL, raw))

    def _create_client(self, url: str, api_key: str | None, timeout_seconds: int):
        if url == ":memory:":
            return QdrantClient(location=":memory:")
        return QdrantClient(url=url, api_key=api_key or None, timeout=timeout_seconds)

    def _point_vector(self, vector: object, embedding_dim: int) -> tuple[float, ...]:
        if isinstance(vector, dict):
            vector = next(iter(vector.values()))
        if isinstance(vector, list):
            values = tuple(float(value) for value in vector)
        else:
            values = tuple(float(value) for value in (vector or ()))
        if len(values) != embedding_dim:
            raise ValueError("Qdrant returned a vector with unexpected dimension")
        return values

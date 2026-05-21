from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models


class EmbeddingVectorService:
    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        embedding_dim: int,
        api_key: str | None = None,
        timeout_seconds: int = 3,
        client: Any | None = None,
    ) -> None:
        if embedding_dim <= 0:
            raise ValueError("embedding_dim must be greater than 0")

        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._client = client or self._create_client(qdrant_url, api_key, timeout_seconds)
        self._last_error: str | None = None

    def ensure_collection(self) -> None:
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
            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
            raise

    def status(self) -> dict[str, object]:
        try:
            self.ensure_collection()
            count = self._client.count(collection_name=self.collection_name, exact=True).count
            return {
                "runtime": "qdrant",
                "collection": self.collection_name,
                "status": "ready",
                "points_count": int(count),
                "last_error": None,
            }
        except Exception as exc:  # pragma: no cover - depends on external Qdrant availability.
            return {
                "runtime": "qdrant",
                "collection": self.collection_name,
                "status": "unavailable",
                "points_count": 0,
                "last_error": str(exc),
            }

    def delete_person(self, person_id: str) -> dict[str, object]:
        try:
            self.ensure_collection()
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
            return {
                "status": "delete_requested",
                "operation_id": getattr(result, "operation_id", None),
                "last_error": None,
            }
        except Exception as exc:  # pragma: no cover - depends on external Qdrant availability.
            self._last_error = str(exc)
            return {
                "status": "unavailable",
                "operation_id": None,
                "last_error": str(exc),
            }

    def _create_client(self, qdrant_url: str, api_key: str | None, timeout_seconds: int):
        if qdrant_url == ":memory:":
            return QdrantClient(location=":memory:")
        return QdrantClient(url=qdrant_url, api_key=api_key or None, timeout=timeout_seconds)

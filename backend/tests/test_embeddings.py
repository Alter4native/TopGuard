from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.services.embeddings import EmbeddingVectorService


def test_embedding_vector_service_creates_collection_and_reports_status() -> None:
    client = QdrantClient(":memory:")
    service = EmbeddingVectorService(
        qdrant_url=":memory:",
        collection_name="person_face_embeddings",
        embedding_dim=4,
        client=client,
    )

    status = service.status()

    assert status["status"] == "ready"
    assert status["collection"] == "person_face_embeddings"
    assert status["points_count"] == 0


def test_embedding_vector_service_deletes_person_points() -> None:
    client = QdrantClient(":memory:")
    service = EmbeddingVectorService(
        qdrant_url=":memory:",
        collection_name="person_face_embeddings",
        embedding_dim=4,
        client=client,
    )
    service.ensure_collection()
    client.upsert(
        collection_name="person_face_embeddings",
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0, 0.0, 0.0],
                payload={"person_id": "person-1"},
            ),
            models.PointStruct(
                id=2,
                vector=[0.0, 1.0, 0.0, 0.0],
                payload={"person_id": "person-2"},
            ),
        ],
        wait=True,
    )

    result = service.delete_person("person-1")
    status = service.status()

    assert result["status"] == "delete_requested"
    assert status["points_count"] == 1

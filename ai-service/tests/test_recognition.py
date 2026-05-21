import pytest
from qdrant_client import QdrantClient

from app.detection.schemas import BoundingBox
from app.recognition.factory import build_embedding_store, build_face_recognizer
from app.recognition.face import SimpleFaceRecognizer
from app.recognition.schemas import FaceRecognitionInput, PersonEmbedding, RecognitionDecision
from app.recognition.vector_store import InMemoryEmbeddingStore, QdrantEmbeddingStore, cosine_similarity


def face_box() -> BoundingBox:
    return BoundingBox(x1=10, y1=10, x2=60, y2=80)


def test_cosine_similarity_matches_equal_vectors() -> None:
    assert cosine_similarity((1.0, 0.0), (1.0, 0.0)) == pytest.approx(1.0)
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)


def test_recognizer_enrolls_and_recognizes_known_person() -> None:
    recognizer = SimpleFaceRecognizer(threshold=0.95, embedding_dim=16)
    recognizer.enroll(
        person_id="person-1",
        photo_id="photo-1",
        image=b"face-image",
        face_bbox=face_box(),
    )

    result = recognizer.recognize(
        FaceRecognitionInput(
            camera_id="camera-1",
            track_id=7,
            image=b"face-image",
            face_bbox=face_box(),
        )
    )

    assert result is not None
    assert result.decision == RecognitionDecision.KNOWN
    assert result.person_id == "person-1"
    assert result.score == pytest.approx(1.0)
    assert result.to_event_result().is_known is True


def test_recognizer_returns_unknown_when_no_match_reaches_threshold() -> None:
    recognizer = SimpleFaceRecognizer(threshold=0.99, embedding_dim=16)
    recognizer.enroll(person_id="person-1", image=b"known-face", face_bbox=face_box())

    result = recognizer.recognize(
        FaceRecognitionInput(
            camera_id="camera-1",
            track_id=8,
            image=b"different-face",
            face_bbox=face_box(),
        )
    )

    assert result is not None
    assert result.decision == RecognitionDecision.UNKNOWN
    assert result.person_id is None
    assert result.to_event_result().is_known is False


def test_recognizer_returns_none_when_face_bbox_is_missing() -> None:
    recognizer = SimpleFaceRecognizer()

    result = recognizer.recognize(
        FaceRecognitionInput(
            camera_id="camera-1",
            track_id=9,
            image=b"body-only",
            face_bbox=None,
        )
    )

    assert result is None


def test_embedding_store_upserts_same_person_photo_model() -> None:
    store = InMemoryEmbeddingStore()
    recognizer = SimpleFaceRecognizer(store=store, embedding_dim=8)

    recognizer.enroll(person_id="person-1", photo_id="photo-1", image=b"one", face_bbox=face_box())
    recognizer.enroll(person_id="person-1", photo_id="photo-1", image=b"two", face_bbox=face_box())

    assert store.count() == 1


def test_embedding_store_deletes_person_embeddings() -> None:
    store = InMemoryEmbeddingStore()
    recognizer = SimpleFaceRecognizer(store=store, embedding_dim=8)

    recognizer.enroll(person_id="person-1", image=b"one", face_bbox=face_box())
    recognizer.enroll(person_id="person-2", image=b"two", face_bbox=face_box())

    assert store.delete_person("person-1") == 1
    assert store.count() == 1


def test_qdrant_embedding_store_upserts_searches_and_deletes() -> None:
    client = QdrantClient(":memory:")
    store = QdrantEmbeddingStore(
        url=":memory:",
        collection_name="person_face_embeddings",
        embedding_dim=4,
        client=client,
    )
    embedding = SimpleFaceRecognizer(embedding_dim=4).embed(image=b"face", face_bbox=face_box())
    store.upsert(PersonEmbedding(person_id="person-1", photo_id="photo-1", embedding=embedding))

    matches = store.search(embedding, limit=1)

    assert store.count() == 1
    assert store.metadata().status == "ready"
    assert matches[0][0].person_id == "person-1"
    assert matches[0][1] == pytest.approx(1.0)
    store.delete_person("person-1")
    assert store.count() == 0


def test_recognition_metadata_reports_enrolled_embeddings() -> None:
    recognizer = SimpleFaceRecognizer(threshold=0.7, embedding_dim=8)
    recognizer.enroll(person_id="person-1", image=b"face", face_bbox=face_box())

    metadata = recognizer.metadata().as_dict()

    assert metadata["runtime"] == "simple"
    assert metadata["threshold"] == 0.7
    assert metadata["embedding_dim"] == 8
    assert metadata["enrolled_embeddings"] == 1
    assert metadata["embedding_store"] == {
        "runtime": "memory",
        "collection": None,
        "status": "ready",
        "last_error": None,
    }
    assert metadata["person_reid_enabled"] is False


def test_recognition_factory_builds_simple_recognizer() -> None:
    recognizer = build_face_recognizer(
        runtime="simple",
        threshold=0.65,
        embedding_dim=32,
        model_name="simple-hash-face-embedding",
    )

    assert recognizer.metadata().runtime == "simple"


def test_recognition_factory_builds_qdrant_embedding_store() -> None:
    store = build_embedding_store(
        runtime="qdrant",
        embedding_dim=4,
        qdrant_url=":memory:",
        qdrant_collection_name="person_face_embeddings",
    )

    assert store.metadata().runtime == "qdrant"


def test_recognition_factory_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported face recognition runtime"):
        build_face_recognizer(
            runtime="unknown",
            threshold=0.65,
            embedding_dim=32,
            model_name="model",
        )


def test_recognizer_validates_threshold_and_dimension() -> None:
    with pytest.raises(ValueError, match="threshold"):
        SimpleFaceRecognizer(threshold=1.5)
    with pytest.raises(ValueError, match="embedding_dim"):
        SimpleFaceRecognizer(embedding_dim=0)

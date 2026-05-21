from datetime import datetime
from uuid import uuid4

from src.auth.passwords import hash_password
from src.schemas.domain import (
    CameraCreate,
    CameraRead,
    CameraStatusUpdate,
    CameraUpdate,
    EventIngest,
    EventRead,
    EventType,
    ModelVersionRead,
    PersonCreate,
    PersonEmbeddingCreate,
    PersonEmbeddingRead,
    PersonPhotoRead,
    PersonRead,
    Role,
    SettingsRead,
    SettingsUpdate,
    UserRecord,
    utc_now,
)


class NotFoundError(LookupError):
    pass


class AppStore:
    def __init__(self) -> None:
        self.users: dict[str, UserRecord] = {}
        self.cameras: dict[str, CameraRead] = {}
        self.events: dict[str, EventRead] = {}
        self.persons: dict[str, PersonRead] = {}
        self.person_photos: dict[str, list[PersonPhotoRead]] = {}
        self.person_embeddings: dict[str, list[PersonEmbeddingRead]] = {}
        self.models: dict[str, ModelVersionRead] = {}
        self.settings = SettingsRead()
        self._seed()

    def _seed(self) -> None:
        self.add_user(username="admin", password="admin", role=Role.ADMIN)
        self.add_user(username="operator", password="operator", role=Role.OPERATOR)
        self.add_user(username="viewer", password="viewer", role=Role.VIEWER)
        self.create_camera(
            CameraCreate(
                name="Local camera",
                source_type="webcam",
                source_uri="0",
                enabled=True,
                processing_fps=5,
            )
        )
        model_id = str(uuid4())
        self.models[model_id] = ModelVersionRead(
            model_id=model_id,
            name="YOLO person detector",
            version="mvp",
            runtime="yolo",
            path="/app/models/yolo-person.pt",
            active=True,
            created_at=utc_now(),
        )

    def add_user(self, username: str, password: str, role: Role) -> UserRecord:
        user = UserRecord(username=username, password_hash=hash_password(password), role=role)
        self.users[user.username] = user
        return user

    def get_user(self, username: str) -> UserRecord | None:
        return self.users.get(username)

    def create_camera(self, payload: CameraCreate) -> CameraRead:
        now = utc_now()
        camera = CameraRead(
            camera_id=str(uuid4()),
            name=payload.name,
            source_type=payload.source_type,
            source_uri=payload.source_uri,
            enabled=payload.enabled,
            processing_fps=payload.processing_fps,
            created_at=now,
            updated_at=now,
        )
        self.cameras[camera.camera_id] = camera
        return camera

    def list_cameras(self) -> list[CameraRead]:
        return list(self.cameras.values())

    def get_camera(self, camera_id: str) -> CameraRead:
        try:
            return self.cameras[camera_id]
        except KeyError as exc:
            raise NotFoundError("Camera not found") from exc

    def update_camera(self, camera_id: str, payload: CameraUpdate) -> CameraRead:
        camera = self.get_camera(camera_id)
        updated = camera.model_copy(
            update={
                key: value
                for key, value in payload.model_dump(exclude_none=True).items()
            }
            | {"updated_at": utc_now()}
        )
        self.cameras[camera_id] = updated
        return updated

    def update_camera_status(self, camera_id: str, payload: CameraStatusUpdate) -> CameraRead:
        camera = self.get_camera(camera_id)
        updated = camera.model_copy(
            update={
                "state": payload.state,
                "last_frame_at": payload.last_frame_at,
                "last_error": payload.last_error,
                "updated_at": utc_now(),
            }
        )
        self.cameras[camera_id] = updated
        return updated

    def ingest_events(self, payloads: list[EventIngest]) -> list[EventRead]:
        events: list[EventRead] = []
        for payload in payloads:
            event = EventRead(
                event_id=payload.event_id or str(uuid4()),
                camera_id=payload.camera_id,
                event_type=payload.event_type,
                timestamp=payload.timestamp or utc_now(),
                confidence=payload.confidence,
                snapshot_url=payload.snapshot_url,
                metadata=payload.metadata,
            )
            self.events[event.event_id] = event
            events.append(event)
        return events

    def list_events(
        self,
        camera_id: str | None = None,
        event_type: EventType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[EventRead]:
        events = list(self.events.values())
        if camera_id is not None:
            events = [event for event in events if event.camera_id == camera_id]
        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]
        if date_from is not None:
            events = [event for event in events if event.timestamp >= date_from]
        if date_to is not None:
            events = [event for event in events if event.timestamp <= date_to]
        return sorted(events, key=lambda event: event.timestamp, reverse=True)

    def get_event(self, event_id: str) -> EventRead:
        try:
            return self.events[event_id]
        except KeyError as exc:
            raise NotFoundError("Event not found") from exc

    def create_person(self, payload: PersonCreate) -> PersonRead:
        now = utc_now()
        person = PersonRead(
            person_id=str(uuid4()),
            display_name=payload.display_name,
            external_id=payload.external_id,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        self.persons[person.person_id] = person
        self.person_photos[person.person_id] = []
        self.person_embeddings[person.person_id] = []
        return person

    def list_persons(self) -> list[PersonRead]:
        return [
            person.model_copy(update={"photo_count": len(self.person_photos.get(person.person_id, []))})
            for person in self.persons.values()
        ]

    def get_person(self, person_id: str) -> PersonRead:
        try:
            person = self.persons[person_id]
        except KeyError as exc:
            raise NotFoundError("Person not found") from exc
        return person.model_copy(update={"photo_count": len(self.person_photos.get(person_id, []))})

    def add_person_photo(
        self,
        person_id: str,
        filename: str,
        content_type: str | None,
    ) -> PersonPhotoRead:
        self.get_person(person_id)
        photo = PersonPhotoRead(
            photo_id=str(uuid4()),
            person_id=person_id,
            filename=filename,
            content_type=content_type,
            created_at=utc_now(),
        )
        self.person_photos.setdefault(person_id, []).append(photo)
        return photo

    def add_person_embedding(
        self,
        person_id: str,
        payload: PersonEmbeddingCreate,
    ) -> PersonEmbeddingRead:
        self.get_person(person_id)
        embedding = PersonEmbeddingRead(
            profile_id=str(uuid4()),
            person_id=person_id,
            photo_id=payload.photo_id,
            embedding_model=payload.embedding_model,
            embedding_dim=payload.embedding_dim,
            vector_collection=payload.vector_collection,
            threshold=payload.threshold,
            active=True,
            created_at=utc_now(),
        )
        self.person_embeddings.setdefault(person_id, []).append(embedding)
        return embedding

    def delete_person_embeddings(self, person_id: str) -> int:
        self.get_person(person_id)
        deleted = len(self.person_embeddings.get(person_id, []))
        self.person_embeddings[person_id] = []
        return deleted

    def list_models(self) -> list[ModelVersionRead]:
        return list(self.models.values())

    def get_settings(self) -> SettingsRead:
        return self.settings

    def update_settings(self, payload: SettingsUpdate) -> SettingsRead:
        self.settings = self.settings.model_copy(update=payload.model_dump(exclude_none=True))
        return self.settings


store = AppStore()

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.passwords import hash_password
from src.db.models import (
    CameraModel,
    EventModel,
    EventSnapshotModel,
    ModelVersionModel,
    PersonModel,
    PersonPhotoModel,
    RoleModel,
    SettingModel,
    UserModel,
    UserRoleModel,
)
from src.schemas.domain import (
    CameraCreate,
    CameraRead,
    CameraState,
    EventIngest,
    EventRead,
    ModelVersionRead,
    PersonCreate,
    PersonPhotoRead,
    PersonRead,
    Role,
    SettingsRead,
    utc_now,
)


def new_id() -> str:
    return str(uuid4())


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_user(self, username: str, password: str, role: Role) -> UserModel:
        role_model = self.session.scalar(select(RoleModel).where(RoleModel.name == role.value))
        if role_model is None:
            role_model = RoleModel(role_id=new_id(), name=role.value)
            self.session.add(role_model)
            self.session.flush()

        user = UserModel(
            user_id=new_id(),
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
        self.session.add(user)
        self.session.flush()
        self.session.add(UserRoleModel(user_id=user.user_id, role_id=role_model.role_id))
        return user

    def get_by_username(self, username: str) -> UserModel | None:
        return self.session.scalar(select(UserModel).where(UserModel.username == username))


class CameraRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: CameraCreate) -> CameraRead:
        now = utc_now()
        camera = CameraModel(
            camera_id=new_id(),
            name=payload.name,
            source_type=payload.source_type,
            source_uri=payload.source_uri,
            enabled=payload.enabled,
            processing_fps=payload.processing_fps,
            state=CameraState.STOPPED.value,
            created_at=now,
            updated_at=now,
        )
        self.session.add(camera)
        self.session.flush()
        return camera_to_read(camera)

    def list(self) -> list[CameraRead]:
        cameras = self.session.scalars(select(CameraModel)).all()
        return [camera_to_read(camera) for camera in cameras]


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest(self, payloads: Sequence[EventIngest]) -> list[EventRead]:
        events: list[EventRead] = []
        for payload in payloads:
            event = EventModel(
                event_id=payload.event_id or new_id(),
                camera_id=payload.camera_id,
                event_type=payload.event_type.value,
                timestamp=payload.timestamp or utc_now(),
                confidence=payload.confidence,
                metadata_json=payload.metadata,
                created_at=utc_now(),
            )
            self.session.add(event)
            self.session.flush()

            if payload.snapshot_url:
                self.session.add(
                    EventSnapshotModel(
                        snapshot_id=new_id(),
                        event_id=event.event_id,
                        storage_key=payload.snapshot_url,
                        content_type="image/jpeg",
                        created_at=utc_now(),
                    )
                )

            events.append(event_to_read(event, payload.snapshot_url))

        return events


class PersonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, payload: PersonCreate) -> PersonRead:
        now = utc_now()
        person = PersonModel(
            person_id=new_id(),
            display_name=payload.display_name,
            external_id=payload.external_id,
            notes=payload.notes,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(person)
        self.session.flush()
        return person_to_read(person, photo_count=0)

    def add_photo(
        self,
        person_id: str,
        filename: str,
        storage_key: str,
        content_type: str | None,
    ) -> PersonPhotoRead:
        photo = PersonPhotoModel(
            photo_id=new_id(),
            person_id=person_id,
            filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            created_at=utc_now(),
        )
        self.session.add(photo)
        self.session.flush()
        return PersonPhotoRead(
            photo_id=photo.photo_id,
            person_id=photo.person_id,
            filename=photo.filename,
            content_type=photo.content_type,
            created_at=photo.created_at,
        )


class ModelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[ModelVersionRead]:
        models = self.session.scalars(select(ModelVersionModel)).all()
        return [
            ModelVersionRead(
                model_id=model.model_id,
                name=model.name,
                version=model.version,
                runtime=model.runtime,
                path=model.path,
                active=model.active,
                created_at=model.created_at,
            )
            for model in models
        ]


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_global(self) -> SettingsRead:
        setting = self.session.get(SettingModel, "global")
        if setting is None:
            return SettingsRead()
        return SettingsRead(**setting.value)


def camera_to_read(camera: CameraModel) -> CameraRead:
    return CameraRead(
        camera_id=camera.camera_id,
        name=camera.name,
        source_type=camera.source_type,
        source_uri=camera.source_uri,
        enabled=camera.enabled,
        processing_fps=camera.processing_fps,
        state=CameraState(camera.state),
        last_frame_at=camera.last_frame_at,
        last_error=camera.last_error,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


def event_to_read(event: EventModel, snapshot_url: str | None) -> EventRead:
    return EventRead(
        event_id=event.event_id,
        camera_id=event.camera_id or "",
        event_type=event.event_type,
        timestamp=event.timestamp,
        confidence=event.confidence,
        snapshot_url=snapshot_url,
        metadata=event.metadata_json,
    )


def person_to_read(person: PersonModel, photo_count: int) -> PersonRead:
    return PersonRead(
        person_id=person.person_id,
        display_name=person.display_name,
        external_id=person.external_id,
        notes=person.notes,
        photo_count=photo_count,
        created_at=person.created_at,
        updated_at=person.updated_at,
    )


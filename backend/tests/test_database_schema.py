from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db.base import Base
from src.db.models import CameraModel, ModelVersionModel, RoleModel, UserModel
from src.db.seed import seed_database


EXPECTED_TABLES = {
    "roles",
    "users",
    "user_roles",
    "cameras",
    "camera_settings",
    "restricted_zones",
    "events",
    "event_snapshots",
    "persons",
    "person_photos",
    "recognition_profiles",
    "model_versions",
    "settings",
    "audit_logs",
    "retention_jobs",
}


def test_sqlalchemy_metadata_contains_expected_tables_and_indexes() -> None:
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))

    events = Base.metadata.tables["events"]
    index_names = {index.name for index in events.indexes}
    assert {
        "ix_events_camera_created",
        "ix_events_type_created",
        "ix_events_camera_type_created",
    }.issubset(index_names)


def test_alembic_upgrade_creates_initial_schema(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "schema.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()

    alembic_cfg = Config("database/alembic.ini")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    inspector = inspect(engine)

    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
    event_indexes = {index["name"] for index in inspector.get_indexes("events")}
    assert "ix_events_camera_type_created" in event_indexes

    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    assert "events" not in set(inspector.get_table_names())

    get_settings.cache_clear()


def test_seed_database_creates_dev_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_database(session)
        session.commit()

        role_names = set(session.scalars(select(RoleModel.name)).all())
        usernames = set(session.scalars(select(UserModel.username)).all())
        cameras = session.scalars(select(CameraModel)).all()
        models = session.scalars(select(ModelVersionModel)).all()

    assert role_names == {"admin", "operator", "viewer"}
    assert {"admin", "operator", "viewer"}.issubset(usernames)
    assert len(cameras) == 1
    assert cameras[0].name == "Local camera"
    assert len(models) == 1
    assert models[0].runtime == "yolo"

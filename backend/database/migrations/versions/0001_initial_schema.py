"""initial database schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("role_id", name=op.f("pk_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_roles_name")),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)
    op.create_table(
        "cameras",
        sa.Column("camera_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("processing_fps", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("last_frame_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("camera_id", name=op.f("pk_cameras")),
    )
    op.create_table(
        "persons",
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("person_id", name=op.f("pk_persons")),
        sa.UniqueConstraint("external_id", name=op.f("uq_persons_external_id")),
    )
    op.create_index(op.f("ix_persons_display_name"), "persons", ["display_name"], unique=False)
    op.create_table(
        "model_versions",
        sa.Column("model_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("runtime", sa.String(length=80), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("model_id", name=op.f("pk_model_versions")),
    )
    op.create_index("ix_model_versions_name_version", "model_versions", ["name", "version"], unique=False)
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )
    op.create_table(
        "retention_jobs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("deleted_events", sa.Integer(), nullable=False),
        sa.Column("deleted_snapshots", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_retention_jobs")),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_user_roles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_table(
        "camera_settings",
        sa.Column("camera_id", sa.String(length=36), nullable=False),
        sa.Column("person_confidence_threshold", sa.Float(), nullable=False),
        sa.Column("face_recognition_threshold", sa.Float(), nullable=False),
        sa.Column("event_cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], name=op.f("fk_camera_settings_camera_id_cameras"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("camera_id", name=op.f("pk_camera_settings")),
    )
    op.create_table(
        "restricted_zones",
        sa.Column("zone_id", sa.String(length=36), nullable=False),
        sa.Column("camera_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("polygon", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], name=op.f("fk_restricted_zones_camera_id_cameras"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("zone_id", name=op.f("pk_restricted_zones")),
    )
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("camera_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], name=op.f("fk_events_camera_id_cameras"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_events")),
    )
    op.create_index("ix_events_camera_created", "events", ["camera_id", "created_at"], unique=False)
    op.create_index("ix_events_type_created", "events", ["event_type", "created_at"], unique=False)
    op.create_index("ix_events_camera_type_created", "events", ["camera_id", "event_type", "created_at"], unique=False)
    op.create_table(
        "person_photos",
        sa.Column("photo_id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.person_id"], name=op.f("fk_person_photos_person_id_persons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id", name=op.f("pk_person_photos")),
    )
    op.create_table(
        "recognition_profiles",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("vector_collection", sa.String(length=160), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.person_id"], name=op.f("fk_recognition_profiles_person_id_persons"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id", name=op.f("pk_recognition_profiles")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("audit_id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"], unique=False)
    op.create_table(
        "event_snapshots",
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"], name=op.f("fk_event_snapshots_event_id_events"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("snapshot_id", name=op.f("pk_event_snapshots")),
        sa.UniqueConstraint("event_id", name=op.f("uq_event_snapshots_event_id")),
    )


def downgrade() -> None:
    op.drop_table("event_snapshots")
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("recognition_profiles")
    op.drop_table("person_photos")
    op.drop_index("ix_events_camera_type_created", table_name="events")
    op.drop_index("ix_events_type_created", table_name="events")
    op.drop_index("ix_events_camera_created", table_name="events")
    op.drop_table("events")
    op.drop_table("restricted_zones")
    op.drop_table("camera_settings")
    op.drop_table("user_roles")
    op.drop_table("retention_jobs")
    op.drop_table("settings")
    op.drop_index("ix_model_versions_name_version", table_name="model_versions")
    op.drop_table("model_versions")
    op.drop_index(op.f("ix_persons_display_name"), table_name="persons")
    op.drop_table("persons")
    op.drop_table("cameras")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
    op.drop_table("roles")


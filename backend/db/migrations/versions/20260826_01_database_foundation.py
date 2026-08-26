"""database foundation for cases, evidence, devices and recordings

Revision ID: 20260826_01
Revises:
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa

revision = "20260826_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "cases" not in tables:
        op.create_table(
        "cases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("investigator", sa.String(), nullable=False),
        sa.Column("case_number", sa.String(length=100), nullable=True, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("owner_auth_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_cases_owner_auth_id", "cases", ["owner_auth_id"])
    else:
        existing = {column["name"] for column in inspector.get_columns("cases")}
        with op.batch_alter_table("cases") as batch:
            if "case_number" not in existing:
                batch.add_column(sa.Column("case_number", sa.String(length=100), nullable=True))
            if "description" not in existing:
                batch.add_column(sa.Column("description", sa.Text(), nullable=True))
            if "status" not in existing:
                batch.add_column(sa.Column("status", sa.String(length=50), nullable=False, server_default="open"))
            if "owner_auth_id" not in existing:
                batch.add_column(sa.Column("owner_auth_id", sa.String(length=64), nullable=True))
        op.create_index("ix_cases_owner_auth_id", "cases", ["owner_auth_id"], if_not_exists=True)

    if "evidence" not in tables:
        op.create_table(
        "evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("original_path", sa.String(), nullable=False),
        sa.Column("working_copy_path", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("md5", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("ACQUIRED", "HASHED", "VERIFIED", "TAMPERED", name="evidencestatus"), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=True),
        sa.Column("parse_warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("parse_errors", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
    else:
        existing = {column["name"] for column in inspector.get_columns("evidence")}
        with op.batch_alter_table("evidence") as batch:
            if "vendor" not in existing:
                batch.add_column(sa.Column("vendor", sa.String(length=100), nullable=True))
            if "parser_version" not in existing:
                batch.add_column(sa.Column("parser_version", sa.String(length=50), nullable=True))
            if "parse_warnings" not in existing:
                batch.add_column(sa.Column("parse_warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
            if "parse_errors" not in existing:
                batch.add_column(sa.Column("parse_errors", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    if "devices" not in tables:
        op.create_table(
        "devices",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("evidence_id", sa.String(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("firmware_version", sa.String(length=255), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("evidence_id", "vendor", name="uq_device_evidence_vendor"),
        )
        op.create_index("ix_devices_evidence_id", "devices", ["evidence_id"])
        op.create_index("ix_devices_vendor", "devices", ["vendor"])
    if "recordings" not in tables:
        op.create_table(
        "recordings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("evidence_id", sa.String(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("device_id", sa.String(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("camera_id", sa.String(length=100), nullable=False),
        sa.Column("recording_identifier", sa.String(length=255), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("extracted_path", sa.Text(), nullable=True),
        sa.Column("original_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("resolution", sa.String(length=50), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("codec", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("recovery_status", sa.String(length=50), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.UniqueConstraint("evidence_id", "recording_identifier", name="uq_recording_evidence_identifier"),
        )
        op.create_index("ix_recordings_evidence_id", "recordings", ["evidence_id"])
        op.create_index("ix_recordings_device_id", "recordings", ["device_id"])
        op.create_index("ix_recordings_camera_id", "recordings", ["camera_id"])


def downgrade() -> None:
    op.drop_table("recordings")
    op.drop_table("devices")
    op.drop_table("evidence")
    op.drop_index("ix_cases_owner_auth_id", table_name="cases")
    op.drop_table("cases")

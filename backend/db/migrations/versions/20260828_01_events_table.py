"""events table for AI/motion detection results

Revision ID: 20260828_01
Revises: 20260826_01
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa

revision = "20260828_01"
down_revision = "20260826_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("evidence_id", sa.String(), sa.ForeignKey("evidence.id"), nullable=False),
        sa.Column("recording_id", sa.String(), sa.ForeignKey("recordings.id"), nullable=True),
        sa.Column("case_id", sa.String(), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("camera_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("track_id", sa.String(length=50), nullable=True),
        sa.Column("object_type", sa.String(length=100), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_events_evidence_id", "events", ["evidence_id"])
    op.create_index("ix_events_recording_id", "events", ["recording_id"])
    op.create_index("ix_events_case_id", "events", ["case_id"])
    op.create_index("ix_events_camera_id", "events", ["camera_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_start_time", "events", ["start_time"])


def downgrade() -> None:
    op.drop_table("events")
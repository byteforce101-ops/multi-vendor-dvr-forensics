"""add detection_confidence and detection_info to evidence

Revision ID: 20260830_01
Revises: 20260828_01
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "20260830_01"
down_revision = "20260828_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("detection_confidence", sa.Float(), nullable=True))
    op.add_column("evidence", sa.Column("detection_info", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "detection_info")
    op.drop_column("evidence", "detection_confidence")

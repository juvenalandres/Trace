"""add hr_zone_seconds to activity_stats

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-28 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'activity_stats' AND column_name = 'hr_zone_seconds')"
    ))
    if not result.scalar():
        op.add_column("activity_stats", sa.Column("hr_zone_seconds", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("activity_stats", "hr_zone_seconds")

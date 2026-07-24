"""extend segment_effort unique constraint to include start_time

Revision ID: a1b2c3d4e5f6
Revises: f8d9e0f1a2b3
Create Date: 2026-07-24 08:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_segment_effort_activity", "segment_efforts", type_="unique")
    op.create_unique_constraint(
        "uq_segment_effort_activity",
        "segment_efforts",
        ["segment_id", "activity_id", "start_time"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_segment_effort_activity", "segment_efforts", type_="unique")
    op.create_unique_constraint(
        "uq_segment_effort_activity",
        "segment_efforts",
        ["segment_id", "activity_id"],
    )

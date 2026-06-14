"""add composite indexes for query performance

Revision ID: c1a2b3c4d5e6
Revises: bbd373f4583f
Create Date: 2026-06-11 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c1a2b3c4d5e6'
down_revision: Union[str, None] = 'bbd373f4583f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Activities: composite index for dashboard time-range queries
    op.create_index(
        'ix_activities_user_start_time',
        'activities',
        ['user_id', 'start_time'],
    )

    # Training sessions: composite index for calendar queries
    op.create_index(
        'ix_training_sessions_plan_date',
        'training_sessions',
        ['plan_id', 'scheduled_date'],
    )

    # Activity stats: index on training_load for sport load distribution queries
    op.create_index(
        'ix_activity_stats_training_load',
        'activity_stats',
        ['training_load'],
    )


def downgrade() -> None:
    op.drop_index('ix_activity_stats_training_load', table_name='activity_stats')
    op.drop_index('ix_training_sessions_plan_date', table_name='training_sessions')
    op.drop_index('ix_activities_user_start_time', table_name='activities')

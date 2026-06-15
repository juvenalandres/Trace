"""add segments and segment_efforts tables

Revision ID: f5a6b7c8d9e0
Revises: e401659b052d
Create Date: 2026-06-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))

    op.create_table(
        'segments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sport_type', sa.String(50), nullable=True),
        sa.Column('start_lat', sa.Float(), nullable=False),
        sa.Column('start_lng', sa.Float(), nullable=False),
        sa.Column('end_lat', sa.Float(), nullable=False),
        sa.Column('end_lng', sa.Float(), nullable=False),
        sa.Column('polyline', sa.Text(), nullable=True),
        sa.Column('distance_m', sa.Float(), nullable=True),
        sa.Column('elevation_gain_m', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_segments_user_id', 'segments', ['user_id'])

    op.create_table(
        'segment_efforts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('segment_id', sa.Integer(), sa.ForeignKey('segments.id'), nullable=False),
        sa.Column('activity_id', sa.Integer(), sa.ForeignKey('activities.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('elapsed_time_s', sa.Float(), nullable=False),
        sa.Column('avg_speed', sa.Float(), nullable=True),
        sa.Column('avg_hr', sa.Float(), nullable=True),
        sa.Column('avg_power', sa.Float(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('segment_id', 'activity_id', name='uq_segment_effort_activity'),
    )
    op.create_index('ix_segment_efforts_segment_id', 'segment_efforts', ['segment_id'])
    op.create_index('ix_segment_efforts_activity_id', 'segment_efforts', ['activity_id'])
    op.create_index('ix_segment_efforts_user_id', 'segment_efforts', ['user_id'])


def downgrade() -> None:
    op.drop_table('segment_efforts')
    op.drop_table('segments')
    op.drop_column('users', 'is_admin')

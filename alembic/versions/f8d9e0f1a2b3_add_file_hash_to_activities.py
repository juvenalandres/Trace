"""add file_hash column to activities

Revision ID: f8d9e0f1a2b3
Revises: f7c8d9e0f1a2
Create Date: 2026-07-21 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8d9e0f1a2b3"
down_revision: Union[str, None] = "f7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("activities", sa.Column("file_hash", sa.String(64), nullable=True))
    op.create_index("ix_activities_file_hash", "activities", ["file_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activities_file_hash", table_name="activities")
    op.drop_column("activities", "file_hash")

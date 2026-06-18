"""add block_type column to training_blocks

Revision ID: f7c8d9e0f1a2
Revises: f6b7c8d9e0f1
Create Date: 2026-06-17 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7c8d9e0f1a2"
down_revision: Union[str, None] = "f6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("training_blocks", sa.Column("block_type", sa.String(50), server_default="general", nullable=False))
    op.alter_column("training_blocks", "block_type", server_default=None)


def downgrade() -> None:
    op.drop_column("training_blocks", "block_type")

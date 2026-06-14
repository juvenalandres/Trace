"""replace_session_targets_with_json

Revision ID: e401659b052d
Revises: 71a04673b786
Create Date: 2026-06-11 11:08:25.151288
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


revision: str = 'e401659b052d'
down_revision: Union[str, None] = '71a04673b786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new targets JSON column
    op.add_column('training_sessions', sa.Column('targets', sa.JSON(), nullable=True))

    # Migrate existing data: convert target_type/value/unit to JSON array
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, target_type, target_value, target_unit FROM training_sessions WHERE target_type IS NOT NULL")
    ).fetchall()
    for row in rows:
        session_id, target_type, target_value, target_unit = row
        targets = [{"type": target_type, "value": target_value, "unit": target_unit}]
        conn.execute(
            sa.text("UPDATE training_sessions SET targets = :targets WHERE id = :id"),
            {"targets": json.dumps(targets), "id": session_id}
        )

    # Drop old columns
    op.drop_column('training_sessions', 'target_unit')
    op.drop_column('training_sessions', 'target_type')
    op.drop_column('training_sessions', 'target_value')


def downgrade() -> None:
    # Add old columns back
    op.add_column('training_sessions', sa.Column('target_value', sa.FLOAT(), nullable=True))
    op.add_column('training_sessions', sa.Column('target_type', sa.VARCHAR(length=50), nullable=True))
    op.add_column('training_sessions', sa.Column('target_unit', sa.VARCHAR(length=50), nullable=True))

    # Migrate data back: extract first target from JSON array
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, targets FROM training_sessions WHERE targets IS NOT NULL")
    ).fetchall()
    for row in rows:
        session_id, targets_json = row
        targets = json.loads(targets_json) if isinstance(targets_json, str) else targets_json
        if targets and len(targets) > 0:
            first = targets[0]
            conn.execute(
                sa.text("UPDATE training_sessions SET target_type = :type, target_value = :value, target_unit = :unit WHERE id = :id"),
                {"type": first.get("type"), "value": first.get("value"), "unit": first.get("unit"), "id": session_id}
            )

    # Drop new column
    op.drop_column('training_sessions', 'targets')

"""initial tables

Revision ID: 991b5dce96e9
Revises:
Create Date: 2026-03-14 15:57:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "991b5dce96e9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workout",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("total_distance", sa.Float(), nullable=True),
        sa.Column("total_energy_burned", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_activity_type", "workout", ["activity_type"])
    op.create_index("ix_workout_start_date", "workout", ["start_date"])
    op.create_index("ix_workout_activity_start", "workout", ["activity_type", "start_date"])

    op.create_table(
        "workout_queue",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("workout_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_queue_activity_type", "workout_queue", ["activity_type"])
    op.create_index("ix_workout_queue_status", "workout_queue", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workout_queue_status", table_name="workout_queue")
    op.drop_index("ix_workout_queue_activity_type", table_name="workout_queue")
    op.drop_table("workout_queue")
    op.drop_index("ix_workout_activity_start", table_name="workout")
    op.drop_index("ix_workout_start_date", table_name="workout")
    op.drop_index("ix_workout_activity_type", table_name="workout")
    op.drop_table("workout")

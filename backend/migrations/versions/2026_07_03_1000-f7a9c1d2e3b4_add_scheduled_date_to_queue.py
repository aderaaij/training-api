"""add scheduled_date column to workout_queue

Promotes the workout's scheduled date out of the JSONB ``workout_data`` blob
into a first-class, indexed column so the schedule can be queried (e.g. "what
runs are on this week") and cross-checked against strength sessions for
conflict detection. The column is backfilled from ``workout_data.scheduledDate``
and kept in sync on write; ``workout_data.scheduledDate`` is still populated for
the iOS app, which decodes it there.

Revision ID: f7a9c1d2e3b4
Revises: e6f8a0d3b5c2
Create Date: 2026-07-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a9c1d2e3b4'
down_revision: Union[str, None] = 'e6f8a0d3b5c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workout_queue',
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_workout_queue_scheduled_date', 'workout_queue', ['scheduled_date']
    )
    # Backfill from the JSONB composition. Guard the cast with a date-shaped
    # regex so malformed values are skipped rather than aborting the migration.
    op.execute(
        """
        UPDATE workout_queue
        SET scheduled_date = (workout_data->>'scheduledDate')::timestamptz
        WHERE workout_data ? 'scheduledDate'
          AND workout_data->>'scheduledDate' ~ '^\\d{4}-\\d{2}-\\d{2}'
        """
    )


def downgrade() -> None:
    op.drop_index('ix_workout_queue_scheduled_date', table_name='workout_queue')
    op.drop_column('workout_queue', 'scheduled_date')

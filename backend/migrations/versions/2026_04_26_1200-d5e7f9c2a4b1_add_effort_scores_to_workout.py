"""add effort scores to workout

Revision ID: d5e7f9c2a4b1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e7f9c2a4b1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workout', sa.Column('effort_score', sa.Numeric(3, 1), nullable=True))
    op.add_column('workout', sa.Column('estimated_effort_score', sa.Numeric(3, 1), nullable=True))
    op.create_check_constraint(
        'effort_score_range',
        'workout',
        'effort_score IS NULL OR (effort_score BETWEEN 1 AND 10)',
    )
    op.create_check_constraint(
        'estimated_effort_score_range',
        'workout',
        'estimated_effort_score IS NULL OR (estimated_effort_score BETWEEN 1 AND 10)',
    )


def downgrade() -> None:
    op.drop_constraint('estimated_effort_score_range', 'workout', type_='check')
    op.drop_constraint('effort_score_range', 'workout', type_='check')
    op.drop_column('workout', 'estimated_effort_score')
    op.drop_column('workout', 'effort_score')

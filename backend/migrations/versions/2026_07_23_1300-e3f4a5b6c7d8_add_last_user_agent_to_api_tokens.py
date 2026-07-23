"""add last_user_agent to api_tokens

Records the last client User-Agent seen per token (written by the throttled
last_used_at touch in app/auth.py). Server half of the app version handshake:
lets the admin see which app version each device runs before shipping a
breaking change.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-23 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_tokens', sa.Column('last_user_agent', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('api_tokens', 'last_user_agent')

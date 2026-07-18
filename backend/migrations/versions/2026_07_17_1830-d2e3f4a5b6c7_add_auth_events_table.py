"""add auth_events table

Append-only audit trail of auth and account-management activity (logins,
password changes, token mints/revokes, admin user actions) for the admin
dashboard's activity feed. FKs are SET NULL so the trail survives user
deletion; the attempted username is kept as text for failed logins.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-17 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event', sa.String(length=40), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip', sa.String(length=64), nullable=True),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auth_events_event', 'auth_events', ['event'])
    op.create_index('ix_auth_events_user_id', 'auth_events', ['user_id'])
    op.create_index('ix_auth_events_created_at', 'auth_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_auth_events_created_at', table_name='auth_events')
    op.drop_index('ix_auth_events_user_id', table_name='auth_events')
    op.drop_index('ix_auth_events_event', table_name='auth_events')
    op.drop_table('auth_events')

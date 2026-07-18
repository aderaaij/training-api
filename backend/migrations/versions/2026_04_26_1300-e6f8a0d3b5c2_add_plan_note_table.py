"""add plan_note table

Revision ID: e6f8a0d3b5c2
Revises: d5e7f9c2a4b1
Create Date: 2026-04-26 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'e6f8a0d3b5c2'
down_revision: Union[str, None] = 'd5e7f9c2a4b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plan_note',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', UUID(as_uuid=True), sa.ForeignKey('plans.id', ondelete='CASCADE'), nullable=True),
        sa.Column('kind', sa.String(32), nullable=False),
        sa.Column('summary', sa.String(280), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('importance', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('conversation_id', sa.String(64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('importance BETWEEN 1 AND 3', name='plan_note_importance_range'),
    )
    op.create_index('ix_plan_note_plan_id', 'plan_note', ['plan_id'])
    op.create_index('ix_plan_note_kind', 'plan_note', ['kind'])
    op.create_index('ix_plan_note_conversation_id', 'plan_note', ['conversation_id'])
    op.create_index('ix_plan_note_created_at', 'plan_note', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_plan_note_created_at', table_name='plan_note')
    op.drop_index('ix_plan_note_conversation_id', table_name='plan_note')
    op.drop_index('ix_plan_note_kind', table_name='plan_note')
    op.drop_index('ix_plan_note_plan_id', table_name='plan_note')
    op.drop_table('plan_note')

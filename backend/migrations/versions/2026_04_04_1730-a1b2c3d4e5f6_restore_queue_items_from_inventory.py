"""restore queue items from device inventory for slow burn plan

Revision ID: a1b2c3d4e5f6
Revises: b2321a8b7f43
Create Date: 2026-04-04 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b2321a8b7f43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PLAN_ID = '4f25daa6-e68a-40b8-a129-2b06acd25abd'


def upgrade() -> None:
    conn = op.get_bind()

    # Get all device inventory items
    inventory = conn.execute(sa.text("SELECT * FROM workout_inventory")).fetchall()

    for item in inventory:
        # Check if queue record already exists
        existing = conn.execute(
            sa.text("SELECT id FROM workout_queue WHERE id = :id"),
            {"id": item.id},
        ).fetchone()

        if existing:
            # Just set plan_id on the existing record
            conn.execute(
                sa.text("UPDATE workout_queue SET plan_id = :plan_id WHERE id = :id"),
                {"plan_id": PLAN_ID, "id": item.id},
            )
        else:
            # Determine status from inventory
            status = 'completed' if item.complete else 'synced'

            conn.execute(
                sa.text("""
                    INSERT INTO workout_queue (id, activity_type, title, plan_id, status, created_at, fetched_at)
                    VALUES (:id, 'running', :title, :plan_id, :status, :synced_at, :synced_at)
                """),
                {
                    "id": item.id,
                    "title": item.display_name,
                    "plan_id": PLAN_ID,
                    "status": status,
                    "synced_at": item.synced_at,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Get inventory IDs to know which queue items we created
    inventory_ids = conn.execute(sa.text("SELECT id FROM workout_inventory")).fetchall()

    for row in inventory_ids:
        # Delete the queue items we created (but not the pre-existing one)
        conn.execute(
            sa.text("""
                DELETE FROM workout_queue
                WHERE id = :id AND plan_id = :plan_id
                AND id != '3e7c0f41-1b24-4e51-81bb-06ba39be1f37'
            """),
            {"id": row.id, "plan_id": '4f25daa6-e68a-40b8-a129-2b06acd25abd'},
        )

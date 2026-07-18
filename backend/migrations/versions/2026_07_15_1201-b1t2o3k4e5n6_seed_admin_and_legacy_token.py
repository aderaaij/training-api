"""seed bootstrap admin and legacy API key token

Creates an 'admin' account (password NULL — set later by `cli bootstrap` from
BOOTSTRAP_ADMIN_PASSWORD) and registers the existing API_KEY as a token owned by
that admin, so the iOS app and MCP keep working unchanged after the auth swap.

Idempotent: ON CONFLICT DO NOTHING on both inserts.

Revision ID: b1t2o3k4e5n6
Revises: a1u2s3e4r5s6
Create Date: 2026-07-15 12:01:00.000000

"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.config import get_settings


# revision identifiers, used by Alembic.
revision: str = 'b1t2o3k4e5n6'
down_revision: Union[str, None] = 'a1u2s3e4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, username, password_hash, display_name, role, is_active, created_at)
            VALUES (:id, 'admin', NULL, 'Admin', 'admin', true, :now)
            ON CONFLICT (username) DO NOTHING
            """
        ),
        {"id": uuid.uuid4(), "now": now},
    )
    admin_id = conn.execute(sa.text("SELECT id FROM users WHERE username = 'admin'")).scalar_one()

    api_key = get_settings().api_key
    if api_key:
        token_hash = hashlib.sha256(api_key.encode()).hexdigest()
        conn.execute(
            sa.text(
                """
                INSERT INTO api_tokens (id, user_id, token_hash, name, created_at)
                VALUES (:id, :user_id, :token_hash, 'legacy-api-key', :now)
                ON CONFLICT (token_hash) DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "user_id": admin_id, "token_hash": token_hash, "now": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM api_tokens WHERE name = 'legacy-api-key'"))
    conn.execute(sa.text("DELETE FROM users WHERE username = 'admin'"))

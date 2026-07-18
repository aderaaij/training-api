import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuthEvent(Base):
    """Append-only audit trail of auth and account-management activity.

    Rows survive user deletion (SET NULL) so the trail stays complete; the
    attempted username is kept as text for the same reason (failed logins may
    never resolve to a user at all).
    """

    __tablename__ = "auth_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # login_success / login_failed / login_rate_limited / password_changed /
    # password_reset / token_created / token_revoked / user_created /
    # user_deactivated / user_reactivated
    event: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The affected account.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Who performed it — differs from user_id only for admin actions.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

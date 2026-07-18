"""Recording helper for the auth_events audit trail.

`record_auth_event` only stages the row — the caller's commit carries it, so an
event and the change it describes land atomically. Paths that otherwise write
nothing (failed logins) pass commit=True.
"""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.auth_event import AuthEvent


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def record_auth_event(
    db: Session,
    event: str,
    *,
    username: str | None = None,
    user_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    ip: str | None = None,
    detail: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    db.add(
        AuthEvent(
            event=event,
            username=username,
            user_id=user_id,
            actor_user_id=actor_user_id,
            ip=ip,
            detail=detail,
        )
    )
    if commit:
        db.commit()

"""Authentication endpoints.

Mounted at /api/auth WITHOUT a router-level auth dependency: `login` is public,
while `me` and token revocation enforce auth via the CurrentUser parameter.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import select

from app.auth import CurrentUser
from app.database import DbSession
from app.models.api_token import ApiToken
from app.models.user import User
from app.rate_limit import limiter
from app.security import generate_token, hash_token, verify_password

router = APIRouter()


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LoginRequest(_CamelModel):
    username: str
    password: str
    device_name: str | None = Field(default=None)


class UserOut(_CamelModel):
    id: uuid.UUID
    username: str
    display_name: str
    role: str


class LoginResponse(_CamelModel):
    token: str
    token_id: uuid.UUID  # this session's token id — for revoke-on-logout
    user: UserOut


class TokenOut(_CamelModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None


class MeResponse(_CamelModel):
    user: UserOut
    tokens: list[TokenOut]


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: DbSession) -> LoginResponse:
    username = body.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    # One indistinguishable failure for unknown user / wrong password / disabled
    # login / inactive account — never reveal which.
    if (
        user is None
        or not user.is_active
        or user.password_hash is None
        or not verify_password(user.password_hash, body.password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    raw = generate_token()
    token = ApiToken(user_id=user.id, token_hash=hash_token(raw), name=(body.device_name or "").strip()[:100])
    db.add(token)
    db.commit()
    db.refresh(token)
    return LoginResponse(token=raw, token_id=token.id, user=UserOut.model_validate(user))


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, db: DbSession) -> MeResponse:
    tokens = db.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at)
    ).all()
    return MeResponse(user=UserOut.model_validate(user), tokens=[TokenOut.model_validate(t) for t in tokens])


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    token = db.get(ApiToken, token_id)
    if token is None or token.user_id != user.id:
        # 404 (not 403) so one user can't probe another's token ids.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    db.delete(token)
    db.commit()

"""Password hashing and API-token helpers.

Passwords are hashed with argon2. API tokens are high-entropy random strings;
only their SHA-256 hash is stored (the entropy makes a plain hash safe — there
is nothing to brute-force as there is with a low-entropy password).
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_ph = PasswordHasher()

# Tokens are prefixed so they are recognisable in configs/logs and greppable.
TOKEN_PREFIX = "tapi_"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_token() -> str:
    """Return a fresh opaque API token (shown to the user exactly once)."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return the stored form of a token (what lives in api_tokens.token_hash)."""
    return hashlib.sha256(token.encode()).hexdigest()

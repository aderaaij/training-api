"""token_rejected audit events — a stranded device's silent 401s made visible.

Rejections are throttled in-process (6h window): expired/inactive tokens key
per token (one stranded device = one clean signal), unknown tokens key per IP
(a scanner rotating garbage tokens can't mint a row per attempt). The throttle
map is cleared per test in conftest, since TestClient shares one IP.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models.api_token import ApiToken
from app.models.user import User
from app.security import generate_token, hash_password, hash_token


def _bearer(token: str) -> TestClient:
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def _rejections(client_admin) -> list[dict]:
    return [e for e in client_admin.get("/api/admin/events").json() if e["event"] == "token_rejected"]


def _mint_expired(client, name: str) -> str:
    res = client.post("/api/auth/tokens", json={"name": name, "expiresAt": "2020-01-01T00:00:00Z"})
    assert res.status_code == 201
    return res.json()["token"]


# --- expired ------------------------------------------------------------------

def test_expired_token_records_one_event_per_window(client_a, client_admin):
    dead = _bearer(_mint_expired(client_a, "Old iPhone"))
    # A stranded device retries — three 401s, but only one audit row.
    for _ in range(3):
        assert dead.get("/api/auth/me").status_code == 401

    events = _rejections(client_admin)
    assert len(events) == 1
    assert events[0]["username"] == "alice"
    assert events[0]["detail"]["reason"] == "expired"
    assert events[0]["detail"]["name"] == "Old iPhone"


def test_two_expired_tokens_are_two_events(client_a, client_admin):
    # Distinct tokens = distinct stranded devices = distinct signals.
    _bearer(_mint_expired(client_a, "Old iPhone")).get("/api/auth/me")
    _bearer(_mint_expired(client_a, "Old iPad")).get("/api/auth/me")
    names = {e["detail"]["name"] for e in _rejections(client_admin)}
    assert names == {"Old iPhone", "Old iPad"}


# --- unknown ------------------------------------------------------------------

def test_unknown_token_records_event_with_hint(client_admin):
    raw = generate_token()  # valid format, never stored — i.e. revoked/garbage
    assert _bearer(raw).get("/api/workouts").status_code == 401

    events = _rejections(client_admin)
    assert len(events) == 1
    assert events[0]["username"] is None  # nothing to attribute
    assert events[0]["detail"]["reason"] == "unknown"
    assert events[0]["detail"]["token_hint"] == hash_token(raw)[-6:]
    assert events[0]["ip"] is not None


def test_unknown_tokens_throttle_per_ip(client_admin):
    # A scanner rotating garbage tokens from one IP mints one row, not many.
    for _ in range(4):
        assert _bearer(generate_token()).get("/api/workouts").status_code == 401
    assert len(_rejections(client_admin)) == 1


# --- inactive account ---------------------------------------------------------

def test_inactive_user_token_records_event(session_factory, client_admin):
    # Dashboard deactivation deletes tokens, so this state needs CLI/DB edits —
    # but a still-live token on a deactivated account must surface too.
    with session_factory() as db:
        user = User(username="carol", role="user", display_name="carol",
                    password_hash=hash_password("pw"), is_active=False)
        db.add(user)
        db.flush()
        raw = generate_token()
        db.add(ApiToken(user_id=user.id, token_hash=hash_token(raw), name="Lingering device"))
        db.commit()

    assert _bearer(raw).get("/api/auth/me").status_code == 401
    events = _rejections(client_admin)
    assert len(events) == 1
    assert events[0]["username"] == "carol"
    assert events[0]["detail"] == {"reason": "inactive", "name": "Lingering device"}


# --- no cross-talk ------------------------------------------------------------

def test_login_failure_and_missing_header_record_nothing(client_admin, user_a):
    # Wrong password is login_failed, not token_rejected.
    res = TestClient(app).post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert res.status_code == 401
    # No/malformed Authorization never reaches token auth (HTTPBearer rejects).
    assert TestClient(app).get("/api/workouts").status_code in (401, 403)

    assert _rejections(client_admin) == []

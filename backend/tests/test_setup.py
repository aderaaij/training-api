"""First-run setup endpoints (the browser create-admin flow).

GET /api/auth/setup reports whether setup is open — true iff no admin has a
password, active or not. POST creates (or claims) the admin, returns a signed-
in session, and hard-closes the moment a passworded admin exists.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models.user import User
from app.security import hash_password, verify_password


def _status() -> bool:
    res = TestClient(app).get("/api/auth/setup")
    assert res.status_code == 200
    return res.json()["required"]


def _setup(**over):
    body = {"username": "admin", "password": "hunter2secret", **over}
    return TestClient(app).post("/api/auth/setup", json=body)


def _login(username: str, password: str):
    return TestClient(app).post("/api/auth/login", json={"username": username, "password": password})


def _seed_user(session_factory, username="admin", role="admin", password=None, active=True) -> uuid.UUID:
    with session_factory() as db:
        u = User(
            username=username,
            role=role,
            display_name=username,
            password_hash=hash_password(password) if password else None,
            is_active=active,
        )
        db.add(u)
        db.commit()
        return u.id


def _user_count(session_factory) -> int:
    with session_factory() as db:
        return db.scalar(select(func.count(User.id)))


# --- GET lifecycle -----------------------------------------------------------

def test_required_flips_across_lifecycle(session_factory):
    assert _status() is True  # empty database
    uid = _seed_user(session_factory)  # seeded admin, no password yet
    assert _status() is True
    with session_factory() as db:
        db.get(User, uid).password_hash = hash_password("hunter2secret")
        db.commit()
    assert _status() is False


def test_passworded_regular_user_does_not_close_setup(session_factory, user_a):
    # user_a is a passworded role=user account — setup stays open without an admin.
    assert _status() is True


def test_deactivated_passworded_admin_keeps_setup_closed(session_factory):
    # A deactivated-but-passworded admin must NOT reopen setup: that install
    # has data, and reopening would let anyone on the network claim it.
    _seed_user(session_factory, password="hunter2secret", active=False)
    assert _status() is False
    assert _setup(username="intruder").status_code == 409


# --- POST creates ------------------------------------------------------------

def test_setup_creates_admin_and_signs_in(session_factory):
    res = _setup(username="  Admin  ", displayName="Head Coach")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"token", "tokenId", "user"}  # same shape as login
    assert body["user"]["username"] == "admin"  # normalized
    assert body["user"]["displayName"] == "Head Coach"
    assert body["user"]["role"] == "admin"

    # The returned token authenticates immediately (the SPA lands signed in).
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {body['token']}"
    assert client.get("/api/auth/me").status_code == 200

    # Setup is now closed, ordinary login works, and the event is on the feed.
    assert _status() is False
    assert _login("admin", "hunter2secret").status_code == 200
    events = client.get("/api/admin/events").json()
    done = [e for e in events if e["event"] == "setup_completed"]
    assert len(done) == 1 and done[0]["username"] == "admin"


def test_setup_claims_null_password_user(session_factory):
    # The seeded bootstrap admin (or any NULL-password account of that name)
    # is claimed rather than erroring: password set, role promoted.
    uid = _seed_user(session_factory, role="user")
    res = _setup()
    assert res.status_code == 200
    assert res.json()["user"]["id"] == str(uid)  # same row, not a duplicate
    assert res.json()["user"]["role"] == "admin"
    assert _user_count(session_factory) == 1
    assert _login("admin", "hunter2secret").status_code == 200


# --- POST guards -------------------------------------------------------------

def test_setup_after_setup_conflicts_and_creates_nothing(session_factory):
    assert _setup().status_code == 200
    before = _user_count(session_factory)
    res = _setup(username="second", password="anotherpass123")
    assert res.status_code == 409
    assert _user_count(session_factory) == before


def test_setup_cannot_hijack_passworded_account(session_factory):
    # No admin exists, so setup is open — but it must never take over an
    # existing passworded (non-admin) account.
    _seed_user(session_factory, username="sofia", role="user", password="sofia-pw-123")
    assert _status() is True
    res = _setup(username="sofia", password="attacker-pw-1")
    assert res.status_code == 409
    with session_factory() as db:
        sofia = db.scalar(select(User).where(User.username == "sofia"))
        assert sofia.role == "user"
        assert verify_password(sofia.password_hash, "sofia-pw-123")  # untouched


def test_setup_validation(session_factory):
    assert _setup(password="short").status_code == 422
    assert _setup(username="has space").status_code == 422
    assert _setup(username="x" * 33).status_code == 422
    assert _user_count(session_factory) == 0  # nothing slipped through

"""last_user_agent capture on api_tokens — server half of the version handshake.

The User-Agent is written by the throttled last_used_at touch in app/auth.py;
a UA change (app updated, different client) bypasses the throttle so the
transition is never missed.
"""


def _me_token(client, name="test-device"):
    me = client.get("/api/auth/me").json()
    return next(t for t in me["tokens"] if t["name"] == name)


def test_user_agent_recorded_and_exposed(client_a):
    client_a.headers["User-Agent"] = "Loopback-iOS/1.0"
    assert client_a.get("/api/auth/me").status_code == 200
    assert _me_token(client_a)["lastUserAgent"] == "Loopback-iOS/1.0"


def test_user_agent_change_bypasses_touch_throttle(client_a):
    client_a.headers["User-Agent"] = "Loopback-iOS/1.0"
    client_a.get("/api/auth/me")
    # Seconds later — well inside the 5-min touch window — the app updates.
    client_a.headers["User-Agent"] = "Loopback-iOS/1.1"
    client_a.get("/api/auth/me")
    assert _me_token(client_a)["lastUserAgent"] == "Loopback-iOS/1.1"


def test_admin_token_list_shows_user_agent(client_admin, client_a, user_a):
    client_a.headers["User-Agent"] = "Loopback-iOS/1.0"
    client_a.get("/api/auth/me")
    tokens = client_admin.get(f"/api/admin/users/{user_a[0]}/tokens").json()
    assert tokens[0]["lastUserAgent"] == "Loopback-iOS/1.0"


def test_oversized_user_agent_truncated(client_a):
    client_a.headers["User-Agent"] = "X" * 1000
    client_a.get("/api/auth/me")
    assert _me_token(client_a)["lastUserAgent"] == "X" * 300

"""The unauthenticated health endpoint — the iOS app's version handshake."""

from fastapi.testclient import TestClient

from app.main import app
from app.version import __version__


def test_health_reports_version():
    resp = TestClient(app).get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "training-api"
    assert body["version"] == __version__
    assert body["database"] == "ok"

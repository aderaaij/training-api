"""Server-managed backups (app/backup.py) + POST /api/admin/backup.

run_backup shells out to a real pg_dump against the test database, so these
also prove the runtime image / CI runner carries a pg_dump that can talk to
the Postgres version in use.
"""

import gzip

import pytest

import app.backup as backup_module
from app.backup import BackupError, _pg_uri, run_backup
from app.config import get_settings

TEST_DB_NAME = "training_api_test"


def _swap_db(uri: str, name: str) -> str:
    return uri.rsplit("/", 1)[0] + "/" + name


@pytest.fixture()
def backup_settings(engine, tmp_path, monkeypatch):
    """Settings pointing run_backup at the test DB and a tmp backup dir."""

    def make(**over):
        s = get_settings().model_copy(
            update={
                "database_url": _swap_db(get_settings().db_uri, TEST_DB_NAME),
                "db_host": None,
                "backup_dir": str(tmp_path),
                **over,
            }
        )
        monkeypatch.setattr(backup_module, "get_settings", lambda: s)
        return s

    return make


def test_pg_uri_strips_driver():
    assert _pg_uri("postgresql+psycopg://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert _pg_uri("postgresql://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"


def test_run_backup_writes_valid_dump(backup_settings, tmp_path):
    backup_settings()
    path = run_backup("test")
    assert path.parent == tmp_path
    assert path.name.startswith("training-api-") and path.name.endswith(".sql.gz")
    with gzip.open(path, "rb") as f:
        content = f.read()
    assert b"PostgreSQL database dump" in content
    assert not list(tmp_path.glob("*.partial"))


def test_run_backup_prunes_to_keep(backup_settings, tmp_path):
    backup_settings(backup_keep=2)
    fakes = [tmp_path / f"training-api-2020010{i}-000000.sql.gz" for i in (1, 2, 3)]
    for f in fakes:
        f.write_bytes(b"old dump")
    (tmp_path / "unrelated.txt").write_text("never pruned")

    path = run_backup("test")
    remaining = sorted(tmp_path.glob("training-api-*.sql.gz"))
    assert remaining == [fakes[2], path]
    assert (tmp_path / "unrelated.txt").exists()


def test_run_backup_missing_dir_raises(backup_settings, tmp_path):
    backup_settings(backup_dir=str(tmp_path / "nope"))
    with pytest.raises(BackupError, match="does not exist"):
        run_backup("test")


def test_backup_endpoint(backup_settings, client_admin):
    backup_settings()
    resp = client_admin.post("/api/admin/backup")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"file", "sizeBytes", "completedAt"}
    assert body["file"].startswith("training-api-")
    assert body["sizeBytes"] > 0


def test_backup_endpoint_unavailable_dir_is_503(backup_settings, tmp_path, client_admin):
    backup_settings(backup_dir=str(tmp_path / "nope"))
    resp = client_admin.post("/api/admin/backup")
    assert resp.status_code == 503
    assert "does not exist" in resp.json()["detail"]


def test_backup_endpoint_rejects_non_admin(client_a):
    assert client_a.post("/api/admin/backup").status_code == 403

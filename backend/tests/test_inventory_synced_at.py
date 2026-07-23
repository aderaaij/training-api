"""synced_at must mean "last time the device reported this item", not "row
first inserted" — the upsert path used to update `complete` in place while
leaving synced_at frozen, so a fresh snapshot looked days old."""

import uuid
from datetime import datetime


def _item(iid=None, day=10, complete=False):
    return {
        "id": iid or str(uuid.uuid4()),
        "displayName": "Run",
        "date": {"year": 2026, "month": 7, "day": day, "hour": 8, "minute": 0},
        "complete": complete,
    }


def _synced_at(client, iid):
    rows = {i["id"]: i for i in client.get("/api/workouts/inventory").json()}
    return datetime.fromisoformat(rows[iid]["synced_at"])


def test_resync_bumps_synced_at_on_updated_rows(client_a):
    item = _item()
    assert client_a.put("/api/workouts/inventory", json=[item]).status_code == 200
    first = _synced_at(client_a, item["id"])

    # Same id, flag flipped in place — the pre-fix behavior kept synced_at frozen.
    item["complete"] = True
    assert client_a.put("/api/workouts/inventory", json=[item]).status_code == 200
    second = _synced_at(client_a, item["id"])

    assert second > first
    assert client_a.get("/api/workouts/inventory").json()[0]["complete"] is True


def test_snapshot_shares_one_timestamp_across_rows(client_a):
    kept = _item(day=1)
    assert client_a.put("/api/workouts/inventory", json=[kept]).status_code == 200

    added = _item(day=2)
    assert client_a.put("/api/workouts/inventory", json=[kept, added]).status_code == 200

    # Updated row and inserted row carry the same snapshot timestamp.
    assert _synced_at(client_a, kept["id"]) == _synced_at(client_a, added["id"])

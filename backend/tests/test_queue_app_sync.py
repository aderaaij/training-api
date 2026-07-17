"""The iOS app's sync confirmation must advance queue items to `synced`.

Bug: newer app builds confirm a watch install with PATCH
/api/workouts/queue/{id}, but only DELETE existed, so every confirmation
405'd and items stayed "pending" forever — the dashboard kept reporting
"N watch items pending sync" for workouts already on the watch.
"""

TS = "2026-07-20T08:00:00+00:00"


def queue_item(client, title="Easy 5K", sched=TS):
    r = client.post("/api/queue", json={"activityType": "running", "title": title, "scheduledDate": sched})
    assert r.status_code == 201
    return r.json()["id"]


def get_item(client, queue_id):
    return next(r for r in client.get("/api/queue").json() if r["id"] == queue_id)


def test_patch_marks_synced(client_a):
    qid = queue_item(client_a)
    assert client_a.patch(f"/api/workouts/queue/{qid}").status_code == 204
    item = get_item(client_a, qid)
    assert item["status"] == "synced"
    assert item["fetched_at"] is not None
    # No longer offered to the app.
    assert all(i["id"] != qid for i in client_a.get("/api/workouts/queue").json())


def test_patch_ignores_any_body(client_a):
    qid = queue_item(client_a)
    r = client_a.patch(f"/api/workouts/queue/{qid}", json={"status": "whatever", "unknown": 1})
    assert r.status_code == 204
    assert get_item(client_a, qid)["status"] == "synced"


def test_patch_never_downgrades_completed(client_a):
    qid = queue_item(client_a)
    assert client_a.patch(f"/api/queue/{qid}/status", json={"status": "completed"}).status_code == 200
    assert client_a.patch(f"/api/workouts/queue/{qid}").status_code == 204
    assert get_item(client_a, qid)["status"] == "completed"


def test_patch_is_owner_scoped(client_a, client_b):
    qid = queue_item(client_a)
    assert client_b.patch(f"/api/workouts/queue/{qid}").status_code == 404
    assert get_item(client_a, qid)["status"] == "pending"


def test_delete_still_marks_synced(client_a):
    qid = queue_item(client_a)
    assert client_a.delete(f"/api/workouts/queue/{qid}").status_code == 204
    assert get_item(client_a, qid)["status"] == "synced"

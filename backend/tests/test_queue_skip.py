"""Skip feedback must retire the queued watch workout.

Bug: runs acknowledged as missed+skip kept status "pending" forever, so the
watch was still offered months-old workouts and the schedule kept warning
about collisions with runs that were never going to happen.
"""

import uuid

TS = "2026-07-20T08:00:00+00:00"  # a Monday


def queue_item(client, title="Easy 5K", sched=TS):
    r = client.post("/api/queue", json={"activityType": "running", "title": title, "scheduledDate": sched})
    assert r.status_code == 201
    return r.json()["id"]


def skip_payload(queue_id, **over):
    p = {
        "id": str(uuid.uuid4()),
        "workoutId": str(queue_id),
        "workoutName": "Easy 5K",
        "scheduledDate": TS,
        "detectedAt": TS,
        "acknowledgedAt": TS,
        "reason": "tired",
        "action": "skip",
        "dismissed": False,
    }
    p.update(over)
    return p


def get_status(client, queue_id):
    return next(r["status"] for r in client.get("/api/queue").json() if r["id"] == queue_id)


def test_skip_feedback_retires_queue_item(client_a):
    qid = queue_item(client_a)
    assert client_a.post("/api/workouts/feedback", json=skip_payload(qid)).status_code == 201
    assert get_status(client_a, qid) == "skipped"
    # The watch endpoints no longer offer it.
    assert all(i["id"] != qid for i in client_a.get("/api/queue/pending").json())
    assert all(i["id"] != qid for i in client_a.get("/api/workouts/queue").json())


def test_non_skip_actions_leave_queue_untouched(client_a):
    qid = queue_item(client_a)
    client_a.post("/api/workouts/feedback", json=skip_payload(qid, action="move", newDate=TS))
    assert get_status(client_a, qid) == "pending"


def test_dismissed_skip_leaves_queue_untouched(client_a):
    qid = queue_item(client_a)
    client_a.post("/api/workouts/feedback", json=skip_payload(qid, dismissed=True))
    assert get_status(client_a, qid) == "pending"


def test_skip_never_downgrades_completed(client_a):
    qid = queue_item(client_a)
    client_a.patch(f"/api/queue/{qid}/status", json={"status": "completed"})
    client_a.post("/api/workouts/feedback", json=skip_payload(qid))
    assert get_status(client_a, qid) == "completed"


def test_cross_user_skip_cannot_touch_others_queue(client_a, client_b):
    qid = queue_item(client_a)
    # B may file feedback naming A's queue id, but A's item must be untouched.
    assert client_b.post("/api/workouts/feedback", json=skip_payload(qid)).status_code == 201
    assert get_status(client_a, qid) == "pending"


def test_skipped_run_stops_conflicting(client_a):
    qid = queue_item(client_a)
    plan = client_a.post(
        "/api/plans", json={"name": "Strength", "activityType": "strength", "startDate": "2026-07-20"}
    ).json()
    sched = client_a.put(
        f"/api/plans/{plan['id']}/schedule",
        json={"startDate": "2026-07-20", "weeks": 1, "days": {"mon": {"title": "Upper A"}}},
    )
    assert sched.status_code == 200
    assert len(sched.json()["warnings"]) == 1  # collides with the queued run

    client_a.post("/api/workouts/feedback", json=skip_payload(qid))

    assert client_a.get(f"/api/plans/{plan['id']}/schedule").json()["warnings"] == []
    cal = client_a.get("/api/schedule/calendar", params={"from": "2026-07-20", "to": "2026-07-20"}).json()
    by_kind = {e["kind"]: e for e in cal["entries"]}
    assert by_kind["run"]["status"] == "skipped"
    assert by_kind["run"]["conflict"] is False
    assert by_kind["strength"]["conflict"] is False

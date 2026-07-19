"""GET /api/workouts/{id}/context — server-held linkage for a synced workout.

The workout id IS the HealthKit UUID the app already tracks, so the iOS app
can resolve "which plan session did this run fulfil, and what feedback exists
for it" in one call. Every key is nullable: an unplanned run has no context.
"""

import uuid
from datetime import datetime

TS = "2026-07-20T08:00:00+00:00"


def make_plan(client, name="10K Block"):
    r = client.post("/api/plans", json={"name": name, "activityType": "running", "startDate": "2026-07-01"})
    assert r.status_code == 201
    return r.json()["id"]


def make_queue_item(client, plan_id=None, title="Easy 5K"):
    payload = {
        "activityType": "running",
        "title": title,
        "scheduledDate": TS,
        "workoutData": {"displayName": title, "scheduledDate": TS},
    }
    if plan_id:
        payload["planId"] = plan_id
    r = client.post("/api/queue", json=payload)
    assert r.status_code == 201
    return r.json()["id"]


def make_workout(client, plan_workout_id=None):
    payload = {
        "id": str(uuid.uuid4()),
        "activityType": "running",
        "startDate": TS,
        "endDate": "2026-07-20T08:45:00+00:00",
        "duration": 2700,
        "totalDistance": 8000,
    }
    if plan_workout_id:
        payload["planWorkoutId"] = str(plan_workout_id)
    r = client.post("/api/workouts", json=payload)
    assert r.status_code == 201
    return payload["id"]


def file_skip_feedback(client, queue_id, reason="tired"):
    r = client.post(
        "/api/workouts/feedback",
        json={
            "id": str(uuid.uuid4()),
            "workoutId": str(queue_id),
            "workoutName": "Easy 5K",
            "scheduledDate": TS,
            "detectedAt": TS,
            "reason": reason,
            "action": "skip",
            "dismissed": False,
        },
    )
    assert r.status_code == 201


def get_context(client, workout_id):
    r = client.get(f"/api/workouts/{workout_id}/context")
    assert r.status_code == 200
    return r.json()


def test_unplanned_workout_has_null_context(client_a):
    wid = make_workout(client_a)
    ctx = get_context(client_a, wid)
    assert ctx["workout_id"] == wid
    assert ctx["plan_workout_id"] is None
    assert ctx["queue_item"] is None
    assert ctx["plan"] is None
    assert ctx["feedback"] is None


def test_planned_workout_resolves_queue_plan_and_feedback(client_a):
    plan_id = make_plan(client_a)
    qid = make_queue_item(client_a, plan_id=plan_id)
    file_skip_feedback(client_a, qid)
    wid = make_workout(client_a, plan_workout_id=qid)

    ctx = get_context(client_a, wid)
    assert ctx["plan_workout_id"] == qid
    assert ctx["queue_item"]["title"] == "Easy 5K"
    assert ctx["queue_item"]["status"] == "skipped"  # live status, not a snapshot
    assert ctx["queue_item"]["plan_id"] == plan_id
    assert ctx["queue_item"]["workout_data"]["displayName"] == "Easy 5K"
    sched = datetime.fromisoformat(ctx["queue_item"]["scheduled_date"].replace("Z", "+00:00"))
    assert sched == datetime.fromisoformat(TS)
    assert ctx["plan"]["id"] == plan_id
    assert ctx["plan"]["name"] == "10K Block"
    assert ctx["feedback"]["action"] == "skip"
    assert ctx["feedback"]["reason"] == "tired"


def test_feedback_survives_queue_deletion(client_a):
    qid = make_queue_item(client_a)
    file_skip_feedback(client_a, qid)
    wid = make_workout(client_a, plan_workout_id=qid)
    assert client_a.delete(f"/api/queue/{qid}").status_code == 204

    ctx = get_context(client_a, wid)
    assert ctx["plan_workout_id"] == qid
    assert ctx["queue_item"] is None
    assert ctx["plan"] is None
    assert ctx["feedback"]["reason"] == "tired"


def test_cross_user_workout_context_404s(client_a, client_b):
    wid = make_workout(client_a)
    assert client_b.get(f"/api/workouts/{wid}/context").status_code == 404


def test_link_to_another_users_queue_item_resolves_null(client_a, client_b):
    # A workout may arrive claiming any plan_workout_id; the joins are
    # user-scoped, so pointing at B's queue item must yield no context.
    other_qid = make_queue_item(client_b)
    file_skip_feedback(client_b, other_qid)
    wid = make_workout(client_a, plan_workout_id=other_qid)

    ctx = get_context(client_a, wid)
    assert ctx["plan_workout_id"] == other_qid
    assert ctx["queue_item"] is None
    assert ctx["plan"] is None
    assert ctx["feedback"] is None

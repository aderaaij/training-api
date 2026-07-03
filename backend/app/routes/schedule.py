"""Unified training calendar: merges scheduled runs (Apple Watch queue) with
recurring strength sessions (from plan schedules), flagging same-day conflicts.

This is the shared timeline the LLM reads to place strength sessions around
existing runs, and that the dashboard renders as a weekly grid.
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.database import DbSession
from app.models.plan import Plan
from app.models.queue import WorkoutQueue
from app.models.workout import Workout
from app.schedule_utils import resolve_sessions

router = APIRouter()

# HealthKit source/activity for completed strength sessions (e.g. Hevy).
STRENGTH_ACTIVITY = "traditionalStrength"


def build_calendar(db: DbSession, date_from: date, date_to: date) -> dict:
    lo = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    hi = datetime.combine(date_to, time.max, tzinfo=timezone.utc)

    # --- Scheduled runs (queued Apple Watch compositions) ---
    run_rows = db.scalars(
        select(WorkoutQueue).where(
            WorkoutQueue.scheduled_date.is_not(None),
            WorkoutQueue.scheduled_date >= lo,
            WorkoutQueue.scheduled_date <= hi,
        )
    ).all()

    # --- Completed strength sessions in the window (for done-matching) ---
    done_rows = db.scalars(
        select(Workout).where(
            Workout.activity_type == STRENGTH_ACTIVITY,
            Workout.start_date >= lo,
            Workout.start_date <= hi,
        )
    ).all()
    done_dates = {w.start_date.date() for w in done_rows}

    # --- Recurring strength sessions from active plan schedules ---
    active_plans = db.scalars(select(Plan).where(Plan.status == "active")).all()

    entries: list[dict] = []

    for r in run_rows:
        d = r.scheduled_date.date()
        entries.append({
            "date": d.isoformat(),
            "kind": "run",
            "title": r.title,
            "activityType": r.activity_type,
            "status": r.status,
            "planId": str(r.plan_id) if r.plan_id else None,
            "planName": None,
            "routineId": None,
            "completed": r.status == "completed",
            "conflict": False,
        })

    for plan in active_plans:
        schedule = (plan.metadata_ or {}).get("schedule")
        for s in resolve_sessions(schedule):
            d = s["date"]
            if d < date_from or d > date_to:
                continue
            entries.append({
                "date": d.isoformat(),
                "kind": "strength",
                "title": s["title"],
                "activityType": plan.activity_type,
                "status": None,
                "planId": str(plan.id),
                "planName": plan.name,
                "routineId": s["routineId"],
                "completed": d in done_dates,
                "conflict": False,
            })

    # --- Flag same-day run/strength collisions ---
    kinds_by_date: dict[str, set] = {}
    for e in entries:
        kinds_by_date.setdefault(e["date"], set()).add(e["kind"])
    for e in entries:
        if {"run", "strength"} <= kinds_by_date[e["date"]]:
            e["conflict"] = True

    entries.sort(key=lambda e: (e["date"], e["kind"]))
    return {"from": date_from.isoformat(), "to": date_to.isoformat(), "entries": entries}


@router.get("/calendar")
def get_calendar(
    db: DbSession,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
):
    """Unified run + strength calendar between ``from`` and ``to`` (defaults to
    today .. +28 days). Each entry carries a ``conflict`` flag when a run and a
    strength session share a date."""
    today = datetime.now(timezone.utc).date()
    date_from = date_from or today
    date_to = date_to or (today + timedelta(days=28))
    return build_calendar(db, date_from, date_to)

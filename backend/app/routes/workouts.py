import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.database import DbSession
from app.models.workout import Workout
from app.schemas.workout import WorkoutCreate, WorkoutList, WorkoutRead, WorkoutSummary

router = APIRouter()


@router.post("", response_model=WorkoutRead, status_code=status.HTTP_201_CREATED)
def create_workout(payload: WorkoutCreate, db: DbSession):
    existing = db.get(Workout, payload.id)
    if existing:
        existing.activity_type = payload.activity_type
        existing.start_date = payload.start_date
        existing.end_date = payload.end_date
        existing.duration = payload.duration
        existing.total_distance = payload.total_distance
        existing.total_energy_burned = payload.total_energy_burned
        existing.source = payload.source
        existing.data = payload.data
        db.commit()
        db.refresh(existing)
        return existing

    workout = Workout(
        id=payload.id,
        activity_type=payload.activity_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration=payload.duration,
        total_distance=payload.total_distance,
        total_energy_burned=payload.total_energy_burned,
        source=payload.source,
        data=payload.data,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return workout


@router.get("", response_model=list[WorkoutList])
def list_workouts(
    db: DbSession,
    activity_type: str | None = None,
    start_after: datetime | None = None,
    start_before: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    q = select(Workout).order_by(Workout.start_date.desc())

    if activity_type:
        q = q.where(Workout.activity_type == activity_type)
    if start_after:
        q = q.where(Workout.start_date >= start_after)
    if start_before:
        q = q.where(Workout.start_date <= start_before)

    q = q.offset(offset).limit(limit)
    return db.scalars(q).all()


@router.get("/summary", response_model=list[WorkoutSummary])
def workout_summary(
    db: DbSession,
    activity_type: str | None = None,
    period: str = Query(default="month", pattern="^(week|month|year)$"),
):
    trunc = func.date_trunc(period, Workout.start_date)

    q = (
        select(
            trunc.label("period"),
            Workout.activity_type,
            func.count().label("count"),
            func.sum(Workout.total_distance).label("total_distance"),
            func.sum(Workout.duration).label("total_duration"),
            func.avg(Workout.total_distance).label("avg_distance"),
            func.avg(Workout.duration).label("avg_duration"),
            func.sum(Workout.total_energy_burned).label("total_energy_burned"),
        )
        .group_by(trunc, Workout.activity_type)
        .order_by(trunc.desc())
    )

    if activity_type:
        q = q.where(Workout.activity_type == activity_type)

    rows = db.execute(q).all()
    return [
        WorkoutSummary(
            period=str(row.period),
            activity_type=row.activity_type,
            count=row.count,
            total_distance=row.total_distance,
            total_duration=row.total_duration,
            avg_distance=float(row.avg_distance) if row.avg_distance else None,
            avg_duration=float(row.avg_duration) if row.avg_duration else None,
            total_energy_burned=row.total_energy_burned,
        )
        for row in rows
    ]


@router.get("/{workout_id}", response_model=WorkoutRead)
def get_workout(workout_id: uuid.UUID, db: DbSession):
    workout = db.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.get("/{workout_id}/splits")
def get_workout_splits(workout_id: uuid.UUID, db: DbSession):
    workout = db.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout.data.get("splits", [])


@router.get("/{workout_id}/heartrate")
def get_workout_heartrate(workout_id: uuid.UUID, db: DbSession):
    workout = db.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout.data.get("heartRateSamples", [])


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: uuid.UUID, db: DbSession):
    workout = db.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    db.delete(workout)
    db.commit()

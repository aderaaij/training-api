import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.database import DbSession
from app.models.plan import Plan
from app.models.queue import WorkoutQueue
from app.schemas.plan import PlanCreate, PlanRead, PlanUpdate
from app.schemas.queue import QueueItemRead

router = APIRouter()


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: DbSession):
    plan = Plan(
        name=payload.name,
        activity_type=payload.activity_type,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        metadata_=payload.metadata,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[PlanRead])
def list_plans(
    db: DbSession,
    plan_status: str | None = Query(default=None, alias="status"),
    activity_type: str | None = None,
):
    q = select(Plan).order_by(Plan.created_at.desc())

    if plan_status:
        q = q.where(Plan.status == plan_status)
    if activity_type:
        q = q.where(Plan.activity_type == activity_type)

    return db.scalars(q).all()


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: uuid.UUID, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: uuid.UUID, payload: PlanUpdate, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    if payload.name is not None:
        plan.name = payload.name
    if payload.activity_type is not None:
        plan.activity_type = payload.activity_type
    if payload.status is not None:
        plan.status = payload.status
    if payload.start_date is not None:
        plan.start_date = payload.start_date
    if payload.end_date is not None:
        plan.end_date = payload.end_date
    if payload.description is not None:
        plan.description = payload.description
    if payload.metadata is not None:
        plan.metadata_ = payload.metadata

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: uuid.UUID, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    db.delete(plan)
    db.commit()


@router.get("/{plan_id}/workouts", response_model=list[QueueItemRead])
def get_plan_workouts(plan_id: uuid.UUID, db: DbSession):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    q = select(WorkoutQueue).where(WorkoutQueue.plan_id == plan_id).order_by(WorkoutQueue.created_at)
    return db.scalars(q).all()

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.database import DbSession
from app.models.queue import WorkoutQueue
from app.schemas.queue import QueueItemCreate, QueueItemRead, QueueStatusUpdate

router = APIRouter()


@router.get("/pending", response_model=list[QueueItemRead])
def get_pending(db: DbSession):
    q = select(WorkoutQueue).where(WorkoutQueue.status == "pending").order_by(WorkoutQueue.created_at)
    return db.scalars(q).all()


@router.get("", response_model=list[QueueItemRead])
def list_queue(
    db: DbSession,
    queue_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    q = select(WorkoutQueue).order_by(WorkoutQueue.created_at.desc())

    if queue_status:
        q = q.where(WorkoutQueue.status == queue_status)

    q = q.offset(offset).limit(limit)
    return db.scalars(q).all()


@router.post("", response_model=QueueItemRead, status_code=status.HTTP_201_CREATED)
def create_queue_item(payload: QueueItemCreate, db: DbSession):
    item = WorkoutQueue(
        activity_type=payload.activity_type,
        title=payload.title,
        description=payload.description,
        workout_data=payload.workout_data,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}/status", response_model=QueueItemRead)
def update_queue_status(item_id: uuid.UUID, payload: QueueStatusUpdate, db: DbSession):
    item = db.get(WorkoutQueue, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")

    now = datetime.now(timezone.utc)
    item.status = payload.status

    if payload.status == "fetched":
        item.fetched_at = now
    elif payload.status == "completed":
        item.completed_at = now

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_queue_item(item_id: uuid.UUID, db: DbSession):
    item = db.get(WorkoutQueue, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    db.delete(item)
    db.commit()


# App-facing router: GET /api/workouts/queue returns pending items,
# DELETE /api/workouts/queue/{id} removes them.
workout_queue_router = APIRouter()


@workout_queue_router.get("")
def app_get_pending(db: DbSession):
    """Return pending queue items as workout compositions for the iOS app.

    Each item's workout_data is returned directly with the queue item's
    id injected, so the app can decode QueuedWorkoutComposition objects.
    """
    q = select(WorkoutQueue).where(WorkoutQueue.status == "pending").order_by(WorkoutQueue.created_at)
    items = db.scalars(q).all()
    results = []
    for item in items:
        composition = dict(item.workout_data or {})
        # Use the queue item's ID so the app can DELETE /api/workouts/queue/{id}
        composition["id"] = str(item.id)
        results.append(composition)
    return results


@workout_queue_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def app_delete_queue_item(item_id: uuid.UUID, db: DbSession):
    item = db.get(WorkoutQueue, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found")
    db.delete(item)
    db.commit()

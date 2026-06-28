import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class QueueItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activity_type: str = Field(alias="activityType")
    title: str
    description: str | None = None
    workout_data: dict | None = Field(default=None, alias="workoutData")
    plan_id: uuid.UUID | None = Field(default=None, alias="planId")


class QueueItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    title: str
    description: str | None
    workout_data: dict | None
    plan_id: uuid.UUID | None
    status: str
    created_at: datetime
    fetched_at: datetime | None
    completed_at: datetime | None

    @computed_field
    @property
    def scheduled_date(self) -> datetime | None:
        raw = (self.workout_data or {}).get("scheduledDate")
        if not isinstance(raw, str):
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None


class QueueItemUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activity_type: str | None = Field(default=None, alias="activityType")
    title: str | None = None
    description: str | None = None
    workout_data: dict | None = Field(default=None, alias="workoutData")
    plan_id: uuid.UUID | None = Field(default=None, alias="planId")


class QueueStatusUpdate(BaseModel):
    status: str

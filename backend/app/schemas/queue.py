import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.validation import ValidationWarning


class QueueItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activity_type: str = Field(alias="activityType")
    title: str
    description: str | None = None
    workout_data: dict | None = Field(default=None, alias="workoutData")
    plan_id: uuid.UUID | None = Field(default=None, alias="planId")
    # Optional explicit override; when omitted the route derives it from
    # workout_data.scheduledDate so existing callers keep working unchanged.
    scheduled_date: datetime | None = Field(default=None, alias="scheduledDate")


class QueueItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    title: str
    description: str | None
    workout_data: dict | None
    plan_id: uuid.UUID | None
    status: str
    scheduled_date: datetime | None
    created_at: datetime
    fetched_at: datetime | None
    completed_at: datetime | None

    @model_validator(mode="after")
    def _fallback_scheduled_date(self) -> "QueueItemRead":
        # The column is authoritative, but fall back to the JSONB composition
        # for any row written before the column existed / was populated.
        if self.scheduled_date is None:
            raw = (self.workout_data or {}).get("scheduledDate")
            if isinstance(raw, str):
                try:
                    self.scheduled_date = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return self


class QueueItemCreatedRead(QueueItemRead):
    """Create response: the item plus schedule-soundness warnings (additive
    key — consumers of the plain item shape are unaffected)."""

    validation: list[ValidationWarning] = []


class QueueBatchCreatedResponse(BaseModel):
    """Batch create response envelope. Warnings cover the athlete's whole
    upcoming schedule, not just the items created in this call."""

    items: list[QueueItemRead]
    validation: list[ValidationWarning] = []


class QueueItemUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    activity_type: str | None = Field(default=None, alias="activityType")
    title: str | None = None
    description: str | None = None
    workout_data: dict | None = Field(default=None, alias="workoutData")
    plan_id: uuid.UUID | None = Field(default=None, alias="planId")
    scheduled_date: datetime | None = Field(default=None, alias="scheduledDate")


class QueueStatusUpdate(BaseModel):
    status: str

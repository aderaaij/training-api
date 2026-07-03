import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class PlanCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    activity_type: str = Field(alias="activityType")
    status: str = "active"
    start_date: date = Field(alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    activity_type: str
    status: str
    start_date: date
    end_date: date | None
    description: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class PlanUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    activity_type: str | None = Field(default=None, alias="activityType")
    status: str | None = None
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    description: str | None = None
    metadata: dict[str, Any] | None = None


# --- Weekly schedule (recurring cadence stored on plan.metadata.schedule) ---


class ScheduleRoutineRef(BaseModel):
    """A single weekday slot in a recurring schedule.

    ``routine_id`` is an opaque reference to an external routine (e.g. a Hevy
    routine id, looked up by the LLM via the hevy-mcp); this API never resolves
    it. Strength slots do not become Apple Watch compositions.
    """

    model_config = ConfigDict(populate_by_name=True)

    title: str
    routine_id: str | None = Field(default=None, alias="routineId")


class PlanSchedule(BaseModel):
    """A weekly recurrence: which routine runs on which weekday, for N weeks."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: date = Field(alias="startDate")
    weeks: int = Field(ge=1, le=52)
    days: dict[str, ScheduleRoutineRef]
    time: str | None = None  # optional "HH:MM" default time of day
    timezone: str | None = None

    @field_validator("days")
    @classmethod
    def _validate_weekdays(cls, v: dict[str, ScheduleRoutineRef]) -> dict[str, ScheduleRoutineRef]:
        if not v:
            raise ValueError("schedule must define at least one weekday")
        bad = [k for k in v if k not in WEEKDAYS]
        if bad:
            raise ValueError(f"invalid weekday keys {bad}; use {list(WEEKDAYS)}")
        return v


class ScheduledSession(BaseModel):
    """One materialised occurrence of a schedule, with run-conflict info."""

    model_config = ConfigDict(populate_by_name=True)

    date: date
    weekday: str
    title: str
    routine_id: str | None = Field(default=None, serialization_alias="routineId")
    conflict: bool = False
    conflicts_with: list[str] = Field(default_factory=list, serialization_alias="conflictsWith")


class PlanScheduleResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    plan_id: uuid.UUID = Field(serialization_alias="planId")
    schedule: PlanSchedule | None
    sessions: list[ScheduledSession] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

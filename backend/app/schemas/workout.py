import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


_KNOWN_FIELDS = {
    "id", "activityType", "startDate", "endDate",
    "duration", "totalDistance", "totalEnergyBurned", "source", "data",
    "planWorkoutId", "effortScore", "estimatedEffortScore",
}


class WorkoutCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    activity_type: str = Field(alias="activityType")
    start_date: datetime = Field(alias="startDate")
    end_date: datetime = Field(alias="endDate")
    duration: float | None = None
    total_distance: float | None = Field(default=None, alias="totalDistance")
    total_energy_burned: float | None = Field(default=None, alias="totalEnergyBurned")
    source: str | None = None
    plan_workout_id: uuid.UUID | None = Field(default=None, alias="planWorkoutId")
    effort_score: float | None = Field(default=None, alias="effortScore", ge=1, le=10)
    estimated_effort_score: float | None = Field(default=None, alias="estimatedEffortScore", ge=1, le=10)
    data: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def collect_extra_into_data(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Collect any extra top-level keys (splits, heartRate, etc.) into data."""
        data = values.get("data", {})
        extra_keys = set(values.keys()) - _KNOWN_FIELDS
        if extra_keys:
            if not isinstance(data, dict):
                data = {}
            for key in extra_keys:
                data[key] = values.pop(key)
            values["data"] = data
        return values


class WorkoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    start_date: datetime
    end_date: datetime
    duration: float | None
    total_distance: float | None
    total_energy_burned: float | None
    source: str | None
    plan_workout_id: uuid.UUID | None
    effort_score: float | None
    estimated_effort_score: float | None
    data: dict
    created_at: datetime
    updated_at: datetime


class WorkoutList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activity_type: str
    start_date: datetime
    end_date: datetime
    duration: float | None
    total_distance: float | None
    total_energy_burned: float | None
    source: str | None
    plan_workout_id: uuid.UUID | None
    effort_score: float | None
    estimated_effort_score: float | None
    created_at: datetime


class WorkoutSummary(BaseModel):
    period: str
    activity_type: str | None
    count: int
    total_distance: float | None
    total_duration: float | None
    avg_distance: float | None
    avg_duration: float | None
    total_energy_burned: float | None

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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

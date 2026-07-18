import uuid

from pydantic import BaseModel


class ValidationWarning(BaseModel):
    code: str
    severity: str  # critical | warn | info
    message: str
    week: str | None = None  # ISO date of the week's Monday
    data: dict = {}
    estimated: bool = False


class WeekSummary(BaseModel):
    week_start: str
    planned_km: float
    actual_km: float
    total_km: float
    run_days: int
    hard_days: int
    longest_km: float
    baseline_km: float | None = None
    ratio: float | None = None
    estimated: bool = False


class PlanValidateResponse(BaseModel):
    plan_id: uuid.UUID
    warnings: list[ValidationWarning]
    weeks: list[WeekSummary]

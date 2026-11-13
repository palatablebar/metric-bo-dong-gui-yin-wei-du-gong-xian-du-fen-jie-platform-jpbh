from __future__ import annotations

from pydantic import BaseModel, Field


class BaselineSuggestIn(BaseModel):
    metric_code: str = Field(default="gmv")
    target_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class AttributionIn(BaseModel):
    metric_code: str = Field(default="gmv")
    target_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    baseline_kind: str | None = Field(default=None, pattern="^(prev_day|same_weekday|median_4w|holiday_shift)$")
    top_n: int = Field(default=8, ge=3, le=20)
    conclusion: str = Field(default="", max_length=2000)


class DrilldownQuery(BaseModel):
    run_id: int = Field(ge=1)

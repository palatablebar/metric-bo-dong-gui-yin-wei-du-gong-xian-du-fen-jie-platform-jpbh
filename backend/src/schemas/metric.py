from __future__ import annotations

from pydantic import BaseModel, Field


class MetricOut(BaseModel):
    id: int
    code: str
    name: str
    unit: str
    kind: str
    kind_label: str
    formula_text: str
    numerator: str | None = None
    denominator: str | None = None
    owner: str
    higher_is_better: bool
    description: str
    decomposable: bool


class MetricPatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    owner: str | None = Field(default=None, max_length=60)
    formula_text: str | None = Field(default=None, max_length=200)
    description: str | None = None
    higher_is_better: bool | None = None


class DimensionMemberOut(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    level: int = 1


class DimensionOut(BaseModel):
    code: str
    label: str
    members: list[DimensionMemberOut] = []
    member_count: int = 0

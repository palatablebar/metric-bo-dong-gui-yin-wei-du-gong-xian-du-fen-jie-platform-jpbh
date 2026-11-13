from __future__ import annotations

from pydantic import BaseModel, Field


class ReportCreateIn(BaseModel):
    run_id: int = Field(ge=1)
    conclusion: str = Field(default="", max_length=2000)


class DeliveryTarget(BaseModel):
    channel: str = Field(default="feishu", pattern="^(feishu|email|wecom)$")
    target: str = Field(default="", max_length=120)


class ReportDistributeIn(BaseModel):
    targets: list[DeliveryTarget] = Field(min_length=1, max_length=4)

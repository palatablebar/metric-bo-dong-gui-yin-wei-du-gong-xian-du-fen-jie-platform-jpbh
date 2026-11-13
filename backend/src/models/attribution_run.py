"""归因批次：一次波动分解的完整口径与结果摘要（落库可复现）。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class AttributionRun(Base):
    __tablename__ = "attribution_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_code: Mapped[str] = mapped_column(String(40), index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    baseline_kind: Mapped[str] = mapped_column(String(24))
    baseline_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="success")
    anomaly_level: Mapped[str] = mapped_column(String(16), default="normal")
    z_score: Mapped[float] = mapped_column(Float, default=0.0)
    mad_value: Mapped[float] = mapped_column(Float, default=0.0)
    value_now: Mapped[float] = mapped_column(Float, default=0.0)
    value_base: Mapped[float] = mapped_column(Float, default=0.0)
    delta_value: Mapped[float] = mapped_column(Float, default=0.0)
    delta_pct: Mapped[float] = mapped_column(Float, default=0.0)
    explained_pct: Mapped[float] = mapped_column(Float, default=0.0)
    residual_value: Mapped[float] = mapped_column(Float, default=0.0)
    top_n: Mapped[int] = mapped_column(Integer, default=8)
    dims: Mapped[list] = mapped_column(JSON, default=list)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    conclusion: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

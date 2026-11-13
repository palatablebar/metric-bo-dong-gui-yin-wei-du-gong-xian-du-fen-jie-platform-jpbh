"""指标口径：公式 + 加法/乘法类型，决定波动分解走哪条算法。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class MetricDef(Base):
    __tablename__ = "metric_defs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(20))              # additive | multiplicative
    formula_text: Mapped[str] = mapped_column(String(200))
    numerator: Mapped[str | None] = mapped_column(String(40), nullable=True)
    denominator: Mapped[str | None] = mapped_column(String(40), nullable=True)
    owner: Mapped[str] = mapped_column(String(60))
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

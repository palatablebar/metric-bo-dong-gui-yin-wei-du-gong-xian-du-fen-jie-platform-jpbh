"""贡献因子：单维成员 / 多维组合 / 量价拆解三类因子。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class SwingFactor(Base):
    __tablename__ = "swing_factors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(16))              # dimension | combo | component
    dim_name: Mapped[str] = mapped_column(String(40))          # city / category / city×category / volume
    member_code: Mapped[str] = mapped_column(String(80))
    member_name: Mapped[str] = mapped_column(String(120))
    path: Mapped[str] = mapped_column(String(160), default="")
    component: Mapped[str | None] = mapped_column(String(20), nullable=True)   # volume | price
    value_now: Mapped[float] = mapped_column(Float, default=0.0)
    value_base: Mapped[float] = mapped_column(Float, default=0.0)
    delta_value: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_pp: Mapped[float] = mapped_column(Float, default=0.0)
    contribution_pct: Mapped[float] = mapped_column(Float, default=0.0)
    share_pct: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

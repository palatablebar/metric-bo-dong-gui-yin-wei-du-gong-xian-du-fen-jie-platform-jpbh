"""日事实明细：5000 条 (日期 × 城市 × 品类 × 渠道 × 门店 × 客群)。

30 天的日粒度聚合由 SQL GROUP BY 派生，不再单独存一张日汇总表。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class FactDaily(Base):
    __tablename__ = "fact_daily"
    __table_args__ = (
        Index("ix_fact_date_city", "stat_date", "city"),
        Index("ix_fact_date_combo", "stat_date", "city", "category", "channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    city: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(40))
    channel: Mapped[str] = mapped_column(String(40))
    store_code: Mapped[str] = mapped_column(String(40))
    segment: Mapped[str] = mapped_column(String(40))
    gmv: Mapped[int] = mapped_column(BigInteger, default=0)
    orders: Mapped[int] = mapped_column(BigInteger, default=0)
    new_members: Mapped[int] = mapped_column(BigInteger, default=0)
    gross_profit: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

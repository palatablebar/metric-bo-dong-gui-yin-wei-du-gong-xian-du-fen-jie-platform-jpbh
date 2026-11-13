"""维度树：5 个维度共 20 个成员，门店挂在城市下（下钻用 parent_code）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class DimTree(Base):
    __tablename__ = "dim_tree"
    __table_args__ = (UniqueConstraint("dimension", "member_code", name="uq_dim_member"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dimension: Mapped[str] = mapped_column(String(20), index=True)
    member_code: Mapped[str] = mapped_column(String(40))
    member_name: Mapped[str] = mapped_column(String(60))
    parent_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

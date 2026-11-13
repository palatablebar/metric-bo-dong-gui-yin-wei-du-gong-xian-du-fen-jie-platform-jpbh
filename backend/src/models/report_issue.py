"""日报：正文 markdown + 结论；分发记录是独立的投递任务（report_deliveries）。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base
from src.models.report_delivery import ReportDelivery
from src.utils.timeutil import utcnow


class ReportIssue(Base):
    __tablename__ = "report_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(200))
    metric_code: Mapped[str] = mapped_column(String(40))
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    markdown: Mapped[str] = mapped_column(Text, default="")
    deliveries: Mapped[list[ReportDelivery]] = relationship(
        cascade="all, delete-orphan",
        order_by="ReportDelivery.id",
        lazy="selectin",
    )
    issued_by: Mapped[str] = mapped_column(String(120), default="")
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

"""投递任务：日报在某个渠道的一次可追踪投递（等待 / 已送达 / 失败）。

幂等约束：(report_id, channel, target) 全表唯一 —— 同一任务重复分发不新增记录；
status != sent 的任务才会被重试，已送达的不再发送。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.constants.enums import DeliveryStatus
from src.models import Base
from src.utils.timeutil import utcnow


class ReportDelivery(Base):
    __tablename__ = "report_deliveries"
    __table_args__ = (
        UniqueConstraint("report_id", "channel", "target", name="uq_delivery_task"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("report_issues.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    target: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(16), default=DeliveryStatus.PENDING.value)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor: Mapped[str] = mapped_column(String(120), default="")
    seed_key: Mapped[str | None] = mapped_column(String(120), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

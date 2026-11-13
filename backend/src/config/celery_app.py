"""Celery 入口：backend 投递任务，worker 消费（心跳 + 每 15 分钟晨会波动巡检）。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

celery_app = Celery(
    "swingattr",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
)

celery_app.conf.beat_schedule = {
    "swingattr-heartbeat": {"task": "swingattr.heartbeat", "schedule": 20.0},
    "swingattr-swing-scan": {"task": "swingattr.scan_swing", "schedule": crontab(minute="*/15")},
}

TASK_HEARTBEAT = "swingattr.heartbeat"
TASK_SCAN_SWING = "swingattr.scan_swing"
TASK_DISPATCH_REPORT = "swingattr.dispatch_report"

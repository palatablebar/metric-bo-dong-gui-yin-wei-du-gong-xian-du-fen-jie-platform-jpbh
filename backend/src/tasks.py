"""Celery 任务：心跳、晨会波动巡检（写 Redis 缓存供前端顶栏）、日报异步分发占位。"""
from __future__ import annotations

import json
import time

from src.config.celery_app import celery_app
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("tasks")


def _redis():
    import redis

    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name="swingattr.heartbeat")
def heartbeat() -> str:
    try:
        _redis().set("swingattr:worker:heartbeat", time.time())
        return "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("heartbeat failed: %s", exc)
        return "error"


@celery_app.task(name="swingattr.scan_swing")
def scan_swing() -> dict:
    """每 15 分钟扫一遍 GMV 最近一日是否有异常波动，把摘要写 Redis。"""
    from src.config.database import session_scope
    from src.services import baseline_service, metric_service
    from src.utils.timeutil import parse_date

    try:
        with session_scope() as db:
            metric = metric_service.get_metric(db, "gmv")
            series = metric_service.daily_series(db, metric, None, 40)
            if not series:
                return {"status": "empty"}
            latest = parse_date(series[-1]["date"])
            payload = baseline_service.suggest(db, metric, latest)
        summary = {
            "generated_at": time.time(),
            "target_date": payload["target_date"],
            "delta_pct": payload["chosen"]["delta_pct"],
            "z_score": payload["z_score"],
            "anomaly_level": payload["anomaly_level"],
            "baseline": payload["chosen"]["kind"],
        }
        _redis().set("swingattr:swing:latest", json.dumps(summary, ensure_ascii=False))
        return summary
    except Exception as exc:  # noqa: BLE001
        logger.warning("scan swing failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@celery_app.task(name="swingattr.dispatch_report")
def dispatch_report(report_id: int) -> dict:
    """异步分发（演示版只回写占位状态，真实渠道需要 webhook 凭据）。"""
    return {"report_id": report_id, "status": "queued"}

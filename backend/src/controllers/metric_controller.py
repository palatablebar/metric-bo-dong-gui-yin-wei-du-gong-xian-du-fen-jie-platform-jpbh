"""指标口径 / 日序列 / 维度树控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, metric_service, tree_service
from src.utils.errors import AppError


def list_metrics(db: Session) -> dict:
    items = metric_service.list_metrics(db)
    return {"items": items, "total": len(items)}


def trend(db: Session, metric_code: str, end_date: str | None, days: int) -> dict:
    metric = metric_service.get_metric(db, metric_code)
    series = metric_service.daily_series(db, metric, end_date, days)
    if not series:
        raise AppError("NO_FACT", 422, detail=f"metric={metric_code}")
    values = [point["value"] for point in series]
    latest = series[-1]
    previous = series[-2] if len(series) > 1 else None
    delta = latest["value"] - previous["value"] if previous else 0.0
    return {
        "metric": metric_service.serialize_metric(metric),
        "series": series,
        "latest": latest,
        "previous": previous,
        "delta_value": round(delta, 2),
        "delta_pct": round(delta / previous["value"] * 100, 2) if previous and previous["value"] else 0.0,
        "peak": max(values) if values else 0,
        "trough": min(values) if values else 0,
        "avg": round(sum(values) / len(values), 2) if values else 0,
        "days": len(series),
    }


def day_detail(db: Session, metric_code: str, day: str) -> dict:
    metric = metric_service.get_metric(db, metric_code)
    payload = metric_service.day_totals(db, metric, day)
    payload["metric"] = metric_service.serialize_metric(metric)
    return payload


def update_metric(db: Session, code: str, payload: dict, actor: dict, request: Request) -> dict:
    metric = metric_service.get_metric(db, code)
    for field, value in payload.items():
        if value is None:
            continue
        setattr(metric, field, value)
    db.flush()
    result = metric_service.serialize_metric(metric)
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="metric.update",
        entity="metric_def",
        entity_id=code,
        detail={"fields": sorted(payload.keys())},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return result


def dimensions(db: Session) -> dict:
    items = tree_service.load_dimensions(db)
    return {
        "items": items,
        "total": len(items),
        "member_total": sum(item["member_count"] for item in items),
    }

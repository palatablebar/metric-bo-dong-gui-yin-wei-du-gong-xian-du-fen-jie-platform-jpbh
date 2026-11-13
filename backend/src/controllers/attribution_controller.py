"""基准线 / 归因 / 下钻控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, baseline_service, metric_service, swing_service, tree_service
from src.utils.timeutil import parse_date


def suggest_baseline(db: Session, payload: dict) -> dict:
    metric = metric_service.get_metric(db, payload["metric_code"])
    return baseline_service.suggest(db, metric, parse_date(payload["target_date"]))


def run(db: Session, payload: dict, actor: dict, request: Request) -> dict:
    metric = metric_service.get_metric(db, payload["metric_code"])
    result = swing_service.run_attribution(
        db,
        metric,
        payload["target_date"],
        payload.get("baseline_kind"),
        int(payload.get("top_n") or 8),
        actor["email"],
        payload.get("conclusion") or "",
    )
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="attribution.run",
        entity="attribution_run",
        entity_id=result["run"]["id"],
        detail={
            "metric": metric.code,
            "target": result["run"]["target_date"],
            "baseline": result["run"]["baseline_date"],
            "delta_pct": result["run"]["delta_pct"],
            "leader": result["factors"][0]["path_label"] if result["factors"] else None,
            "explained_pct": result["run"]["explained_pct"],
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return result


def list_runs(db: Session, limit: int) -> dict:
    return swing_service.list_runs(db, limit)


def get_run(db: Session, run_id: int) -> dict:
    return swing_service.get_run_detail(db, run_id)


def drilldown(db: Session, run_id: int, path: dict[str, str]) -> dict:
    from sqlalchemy import select

    from src.models.attribution_run import AttributionRun

    run_row = db.scalar(select(AttributionRun).where(AttributionRun.id == run_id))
    if run_row is None:
        from src.utils.errors import AppError

        raise AppError("NOT_FOUND", 404, detail=f"run={run_id}")
    return tree_service.drilldown(db, run_row, path)

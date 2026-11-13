"""指标口径 / 趋势 / 维度树。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import METRIC_WRITE_ROLES, READ_ROLES
from src.controllers import metric_controller
from src.middlewares.rbac import require_roles
from src.schemas.metric import MetricPatchIn

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def list_metrics(db: Session = Depends(get_db), _: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return metric_controller.list_metrics(db)


@router.get("/metrics/{metric_code}/trend")
def trend(
    metric_code: str,
    end_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    days: int = Query(default=30, ge=7, le=60),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return metric_controller.trend(db, metric_code, end_date, days)


@router.get("/metrics/{metric_code}/day")
def day_detail(
    metric_code: str,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return metric_controller.day_detail(db, metric_code, date)


@router.patch("/metrics/{metric_code}")
def update_metric(
    metric_code: str,
    payload: MetricPatchIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(*METRIC_WRITE_ROLES)),
) -> dict:
    return metric_controller.update_metric(db, metric_code, payload.model_dump(exclude_none=True), actor, request)


@router.get("/dimensions")
def dimensions(db: Session = Depends(get_db), _: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return metric_controller.dimensions(db)

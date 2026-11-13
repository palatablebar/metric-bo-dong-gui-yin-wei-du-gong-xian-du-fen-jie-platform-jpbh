from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import DISTRIBUTE_ROLES, READ_ROLES, REPORT_WRITE_ROLES
from src.controllers import report_controller
from src.middlewares.rbac import require_roles
from src.schemas.report import ReportCreateIn, ReportDistributeIn

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return report_controller.list_reports(db, limit)


@router.post("", status_code=201)
def create_report(
    payload: ReportCreateIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(*REPORT_WRITE_ROLES)),
) -> dict:
    return report_controller.create(db, payload.model_dump(), actor, request)


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return report_controller.get_report(db, report_id)


@router.post("/{report_id}/distribute")
def distribute(
    report_id: int,
    payload: ReportDistributeIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(*DISTRIBUTE_ROLES)),
) -> dict:
    return report_controller.distribute(db, report_id, payload.model_dump(), actor, request)

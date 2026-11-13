from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import ATTRIBUTION_ROLES, READ_ROLES
from src.controllers import attribution_controller
from src.middlewares.rbac import require_roles
from src.schemas.attribution import AttributionIn

router = APIRouter(prefix="/attributions", tags=["attributions"])


@router.get("")
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return attribution_controller.list_runs(db, limit)


@router.post("", status_code=201)
def run_attribution(
    payload: AttributionIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(*ATTRIBUTION_ROLES)),
) -> dict:
    return attribution_controller.run(db, payload.model_dump(), actor, request)


@router.get("/{run_id}")
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    return attribution_controller.get_run(db, run_id)


@router.get("/{run_id}/drilldown")
def drilldown(
    run_id: int,
    city: str | None = Query(default=None),
    category: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    store: str | None = Query(default=None),
    segment: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    path = {
        key: value
        for key, value in {
            "city": city,
            "category": category,
            "channel": channel,
            "store": store,
            "segment": segment,
        }.items()
        if value
    }
    return attribution_controller.drilldown(db, run_id, path)

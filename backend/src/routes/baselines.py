from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import ATTRIBUTION_ROLES
from src.controllers import attribution_controller
from src.middlewares.rbac import require_roles
from src.schemas.attribution import BaselineSuggestIn

router = APIRouter(prefix="/baselines", tags=["baselines"])


@router.post("/suggest")
def suggest(
    payload: BaselineSuggestIn,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(*ATTRIBUTION_ROLES)),
) -> dict:
    return attribution_controller.suggest_baseline(db, payload.model_dump())

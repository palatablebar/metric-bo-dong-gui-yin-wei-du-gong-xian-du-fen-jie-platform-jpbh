from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import EXPORT_ROLES
from src.controllers import report_controller
from src.middlewares.rbac import require_roles

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/report.md")
def export_report(
    request: Request,
    report_id: int,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(*EXPORT_ROLES)),
) -> Response:
    text, filename = report_controller.export_md(db, report_id, actor, request)
    return Response(
        content=text.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "X-Export-Filename": filename,
        },
    )

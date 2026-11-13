"""日报与分发控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, report_service


def create(db: Session, payload: dict, actor: dict, request: Request) -> dict:
    report = report_service.create_report(db, int(payload["run_id"]), payload.get("conclusion", ""), actor["email"])
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="report.create",
        entity="report_issue",
        entity_id=report["id"],
        detail={"run_id": report["run_id"], "date": report["report_date"]},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return report


def list_reports(db: Session, limit: int) -> dict:
    return report_service.list_reports(db, limit)


def get_report(db: Session, report_id: int) -> dict:
    return report_service.get_report(db, report_id)


def distribute(db: Session, report_id: int, payload: dict, actor: dict, request: Request) -> dict:
    report = report_service.distribute(db, report_id, payload["targets"], actor["email"])
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="report.distribute",
        entity="report_issue",
        entity_id=report_id,
        detail={
            "channels": {item["channel"]: item["status"] for item in report["deliveries"]},
            "dispatch": report["dispatch"],
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return report


def retry_delivery(db: Session, report_id: int, delivery_id: int, actor: dict, request: Request) -> dict:
    report = report_service.retry_delivery(db, report_id, delivery_id, actor["email"])
    task = next(item for item in report["deliveries"] if item["id"] == delivery_id)
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="report.delivery_retry",
        entity="report_delivery",
        entity_id=delivery_id,
        detail={
            "report_id": report_id,
            "channel": task["channel"],
            "result": task["status"],
            "attempts": task["attempts"],
            "last_error": task["last_error"],
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return report


def export_md(db: Session, report_id: int, actor: dict, request: Request) -> tuple[str, str]:
    text, filename = report_service.export_markdown(db, report_id)
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="export.report",
        entity="report_issue",
        entity_id=report_id,
        detail={"filename": filename, "bytes": len(text.encode("utf-8"))},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return text, filename


def audit_logs(db: Session, limit: int) -> dict:
    return audit_service.list_logs(db, limit)

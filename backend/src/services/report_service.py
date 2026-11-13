"""日报：把一次归因批次写成可分发的中文 markdown；分发是按渠道追踪的投递任务。"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from src.constants.enums import (
    DELIVERY_LABELS,
    DELIVERY_STATUS_LABELS,
    REPORT_STATUS_LABELS,
    DeliveryStatus,
    ReportStatus,
    RunStatus,
)
from src.constants.limits import MAX_DELIVERY_TARGETS
from src.models.attribution_run import AttributionRun
from src.models.metric_def import MetricDef
from src.models.report_delivery import ReportDelivery
from src.models.report_issue import ReportIssue
from src.services import delivery_service, swing_service
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, weekday_label


def build_markdown(db: Session, run_row: AttributionRun, factors: list[dict], conclusion: str) -> str:
    metric = db.scalar(select(MetricDef).where(MetricDef.code == run_row.metric_code))
    unit = metric.unit if metric else ""
    direction = "下滑" if run_row.delta_value < 0 else "上涨"
    lines = [
        f"# {run_row.target_date.isoformat()} {metric.name if metric else run_row.metric_code} 波动归因日报",
        "",
        f"- 指标：**{metric.name if metric else run_row.metric_code}**（{unit}）",
        f"- 本期：{run_row.value_now:,.0f}（{weekday_label(run_row.target_date)}）",
        f"- 基线：{run_row.value_base:,.0f}（{run_row.baseline_date.isoformat()} · {run_row.baseline_kind}）",
        f"- 波动：{run_row.delta_value:+,.0f}{unit}（{run_row.delta_pct:+.2f}%），{direction}",
        f"- 稳健异常：|Δ|/MAD = {run_row.z_score:.2f}（MAD {run_row.mad_value:,.0f}）→ {run_row.anomaly_level}",
        f"- 解释度：Top {run_row.top_n} 因子合计 {run_row.explained_pct:.1f}%，残差 {run_row.residual_value:+,.0f}{unit}",
        "",
        "## 贡献因子 Top",
        "",
        "| # | 维度 | 成员 | 本期 | 基线 | Δ | 贡献(pp) | 占总波动 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in factors:
        lines.append(
            f"| {item['rank']} | {item['dim_label']} | {item['path_label']} | "
            f"{item['value_now']:,.0f} | {item['value_base']:,.0f} | {item['delta_value']:+,.0f} | "
            f"{item['contribution_pp']:+.2f} | {item['contribution_pct']:.1f}% |"
        )
    components = (run_row.components or {}).get("items", [])
    if components:
        lines.extend(
            [
                "",
                "## 量价拆解（对数分解 Δln = ln(本期/基线)）",
                "",
                "| 效应 | 本期 | 基线 | Δln | 金额贡献 |",
                "|---|---|---|---|---|",
            ]
        )
        for item in components:
            lines.append(
                f"| {item['label']} | {item['value_now']:,.2f} | {item['value_base']:,.2f} | "
                f"{item['delta_ln']:+.6f} | {item['contribution_value']:+,.0f}{unit} |"
            )
    lines.extend(
        [
            "",
            "## 结论",
            "",
            conclusion or run_row.conclusion or "（待分析师补充）",
            "",
            "## 口径",
            "",
            f"- 基线口径：{run_row.baseline_kind}；稳健离散 MAD={run_row.mad_value:,.0f}",
            "- 组合扫描：城市 × 品类 × 渠道 共 36 个三元组 / 33 个二元组，按 |Δ| 排名取 Top-N",
            "- 残差 = 总波动 − Top-N 因子之和；解释度 = Top-N 之和 / 总波动",
            "",
            f"> 生成于 {date.today().isoformat()} · swingattr",
        ]
    )
    return "\n".join(lines)


def create_report(db: Session, run_id: int, conclusion: str, issued_by: str) -> dict:
    run_row = db.scalar(select(AttributionRun).where(AttributionRun.id == run_id))
    if run_row is None:
        raise AppError("NOT_FOUND", 404, detail=f"run={run_id}")
    if run_row.status == RunStatus.FAILED.value:
        raise AppError("RUN_INCOMPLETE", 422, detail="失败批次不能出日报")
    existing = db.scalar(select(ReportIssue).where(ReportIssue.run_id == run_id))
    if existing is not None:
        return serialize_report(existing)
    metric = db.scalar(select(MetricDef).where(MetricDef.code == run_row.metric_code))
    detail = swing_service.get_run_detail(db, run_id)
    factors = detail["factors"]
    text = conclusion or run_row.conclusion
    markdown = build_markdown(db, run_row, factors, text)
    report = ReportIssue(
        report_date=run_row.target_date,
        title=f"{run_row.target_date.isoformat()} {metric.name if metric else run_row.metric_code} 波动归因日报",
        metric_code=run_row.metric_code,
        run_id=run_id,
        status=ReportStatus.DRAFT.value,
        conclusion=text,
        markdown=markdown,
        issued_by=issued_by,
    )
    db.add(report)
    db.flush()
    return serialize_report(report)


def _validate_targets(targets: list[dict]) -> None:
    if not targets:
        raise AppError("VALIDATION", 422, detail="至少要选一个分发渠道")
    if len(targets) > MAX_DELIVERY_TARGETS:
        raise AppError("VALIDATION", 422, detail=f"最多 {MAX_DELIVERY_TARGETS} 个渠道")
    seen: set[tuple[str, str]] = set()
    for target in targets:
        channel = target.get("channel", "")
        if channel not in DELIVERY_LABELS:
            raise AppError("VALIDATION", 422, detail=f"未知渠道：{channel}")
        key = (channel, target.get("target", ""))
        if key in seen:
            raise AppError("VALIDATION", 422, detail=f"同一渠道和目标重复：{channel}")
        seen.add(key)


def _load_report(db: Session, report_id: int) -> ReportIssue | None:
    stmt = (
        select(ReportIssue)
        .where(ReportIssue.id == report_id)
        .options(selectinload(ReportIssue.deliveries))
    )
    return db.scalar(stmt)


def distribute(db: Session, report_id: int, targets: list[dict], actor: str) -> dict:
    """分发 = 建任务（幂等）+ 续投未送达渠道。

    同一 (渠道, 目标) 已存在任务时不新增记录；已送达的跳过不重发；
    之前失败/等待的任务随本次一起续投。全部送达后日报才发布。
    """
    report = _load_report(db, report_id)
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    _validate_targets(targets)
    existing = {(task.channel, task.target): task for task in report.deliveries}
    new_keys = {(item.get("channel", ""), item.get("target", "")) for item in targets}
    if len(set(existing) | new_keys) > MAX_DELIVERY_TARGETS:
        raise AppError("VALIDATION", 422, detail=f"一份日报最多 {MAX_DELIVERY_TARGETS} 个投递任务")
    created = 0
    for item in targets:
        key = (item.get("channel", ""), item.get("target", ""))
        if key in existing:
            continue  # 幂等：同一任务重复分发不新增记录
        report.deliveries.append(
            ReportDelivery(channel=key[0], target=key[1], actor=actor)
        )
        created += 1
    try:
        db.flush()
    except IntegrityError as exc:
        # 并发重复提交撞上 (report_id, channel, target) 唯一约束：不新增记录，提示刷新
        db.rollback()
        raise AppError("CONFLICT", 409, detail="重复的分发请求，请刷新后查看投递任务") from exc
    summary = delivery_service.dispatch_pending(report)
    summary["created"] = created
    db.flush()
    return {**serialize_report(report), "dispatch": summary}


def retry_delivery(db: Session, report_id: int, delivery_id: int, actor: str) -> dict:
    """单路重试：只补这一个渠道；已送达的任务拒绝重试（不重复发送）。"""
    report = _load_report(db, report_id)
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    task = next((item for item in report.deliveries if item.id == delivery_id), None)
    if task is None:
        raise AppError("NOT_FOUND", 404, detail=f"delivery={delivery_id}")
    if task.status == DeliveryStatus.SENT.value:
        raise AppError("DELIVERY_ALREADY_SENT", 409, detail=f"{DELIVERY_LABELS.get(task.channel, task.channel)} 已送达")
    task.actor = actor
    ok = delivery_service.attempt_delivery(task, report)
    delivery_service.refresh_report_status(report)
    db.flush()
    summary = {"attempted": 1, "sent": int(ok), "failed": int(not ok), "skipped_sent": 0, "created": 0}
    return {**serialize_report(report), "dispatch": summary}


def list_reports(db: Session, limit: int = 20) -> dict:
    stmt = (
        select(ReportIssue)
        .order_by(ReportIssue.id.desc())
        .limit(limit)
        .options(selectinload(ReportIssue.deliveries))
    )
    rows = db.scalars(stmt).all()
    return {"items": [serialize_report(row) for row in rows], "total": len(rows)}


def get_report(db: Session, report_id: int) -> dict:
    report = _load_report(db, report_id)
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    return serialize_report(report)


def serialize_delivery(task: ReportDelivery) -> dict:
    return {
        "id": task.id,
        "channel": task.channel,
        "channel_label": DELIVERY_LABELS.get(task.channel, task.channel),
        "target": task.target,
        "status": task.status,
        "status_label": DELIVERY_STATUS_LABELS.get(task.status, task.status),
        "attempts": task.attempts,
        "last_error": task.last_error,
        "actor": task.actor,
        "created_at": iso_utc(task.created_at),
        "last_attempt_at": iso_utc(task.last_attempt_at),
        "delivered_at": iso_utc(task.delivered_at),
    }


def serialize_report(report: ReportIssue) -> dict:
    tasks = list(report.deliveries)
    sent = sum(1 for task in tasks if task.status == DeliveryStatus.SENT.value)
    failed = sum(1 for task in tasks if task.status == DeliveryStatus.FAILED.value)
    return {
        "id": report.id,
        "report_date": report.report_date.isoformat(),
        "title": report.title,
        "metric_code": report.metric_code,
        "run_id": report.run_id,
        "status": report.status,
        "status_label": REPORT_STATUS_LABELS.get(report.status, report.status),
        "conclusion": report.conclusion,
        "markdown": report.markdown,
        "deliveries": [serialize_delivery(task) for task in tasks],
        "delivery_count": len(tasks),
        "delivery_summary": {
            "total": len(tasks),
            "sent": sent,
            "failed": failed,
            "pending": len(tasks) - sent - failed,
        },
        "issued_by": report.issued_by,
        "created_at": iso_utc(report.created_at),
        "published_at": iso_utc(report.published_at),
    }


def export_markdown(db: Session, report_id: int) -> tuple[str, str]:
    report = db.scalar(select(ReportIssue).where(ReportIssue.id == report_id))
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    filename = f"swingattr-report-{report.report_date.isoformat()}-{report.id}.md"
    return report.markdown, filename

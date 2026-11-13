"""日报：把一次归因批次写成可分发的中文 markdown，并记录分发渠道。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import (
    DELIVERY_LABELS,
    REPORT_STATUS_LABELS,
    ReportStatus,
    RunStatus,
)
from src.constants.limits import MAX_DELIVERY_TARGETS
from src.models.attribution_run import AttributionRun
from src.models.metric_def import MetricDef
from src.models.report_issue import ReportIssue
from src.services import swing_service
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, parse_date, utcnow, weekday_label


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
        deliveries=[],
        issued_by=issued_by,
    )
    db.add(report)
    db.flush()
    return serialize_report(report)


def distribute(db: Session, report_id: int, targets: list[dict], actor: str) -> dict:
    report = db.scalar(select(ReportIssue).where(ReportIssue.id == report_id))
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    if not targets:
        raise AppError("VALIDATION", 422, detail="至少要选一个分发渠道")
    if len(targets) > MAX_DELIVERY_TARGETS:
        raise AppError("VALIDATION", 422, detail=f"最多 {MAX_DELIVERY_TARGETS} 个渠道")
    deliveries = list(report.deliveries or [])
    delivered_at = utcnow().isoformat(timespec="seconds") + "Z"
    for target in targets:
        channel = target.get("channel", "feishu")
        deliveries.append(
            {
                "channel": channel,
                "channel_label": DELIVERY_LABELS.get(channel, channel),
                "target": target.get("target", ""),
                "actor": actor,
                "delivered_at": delivered_at,
                "status": "sent",
            }
        )
    report.deliveries = deliveries
    report.status = ReportStatus.PUBLISHED.value
    if report.published_at is None:
        report.published_at = utcnow()
    db.flush()
    return serialize_report(report)


def list_reports(db: Session, limit: int = 20) -> dict:
    rows = db.scalars(select(ReportIssue).order_by(ReportIssue.id.desc()).limit(limit)).all()
    return {"items": [serialize_report(row) for row in rows], "total": len(rows)}


def get_report(db: Session, report_id: int) -> dict:
    report = db.scalar(select(ReportIssue).where(ReportIssue.id == report_id))
    if report is None:
        raise AppError("NOT_FOUND", 404, detail=f"report={report_id}")
    return serialize_report(report)


def serialize_report(report: ReportIssue) -> dict:
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
        "deliveries": report.deliveries or [],
        "delivery_count": len(report.deliveries or []),
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

"""幂等 seed：3 账号 / 5 指标 / 5 维度 20 成员 / 5000 条日事实 / 2 次归因 / 1 份日报。

自然键 upsert：
  users.email
  metric_defs.code
  dim_tree(dimension, member_code)
  fact_daily(id)  —— 明细整批只有一次：以「该日期是否已有明细」判定，已存在就整日跳过
  attribution_runs.seed_key
  report_issues.seed_key

重复执行不新增、不覆盖用户修改。SEED_SUMMARY 里 runs / reports 只数 seed 自己建的记录，
所以跑过现场归因后重复 seed 计数不会漂移。

两次归因都是真算法跑出来的（分别演示同星期基线 + 节假日位移基线）。
"""
from __future__ import annotations

from sqlalchemy import func, select

from src.config.database import session_scope
from src.constants.enums import DeliveryChannel, ReportStatus
from src.models.attribution_run import AttributionRun
from src.models.audit import AuditLog
from src.models.dim_tree import DimTree
from src.models.fact_daily import FactDaily
from src.models.metric_def import MetricDef
from src.models.report_issue import ReportIssue
from src.models.user import User
from src.services import report_service, swing_service
from src.utils.security import hash_password
from scripts import demo_config as cfg
from scripts.fact_builder import build_facts

DEMO_PASSWORD = "Demo@2026"
DEMO_USERS = [
    ("admin@swingattr.io", "林清河 · 分析负责人", "admin"),
    ("analyst@swingattr.io", "周到 · 分析师", "analyst"),
    ("exec@swingattr.io", "苏未 · 管理层（只读）", "exec"),
]

SEED_RUNS = [
    {
        "seed_key": "seed:run:gmv:2026-11-09",
        "metric": "gmv",
        "target_date": cfg.TARGET_DATE,
        "baseline_kind": "same_weekday",
        "top_n": 12,
        "conclusion": (
            "11-09 GMV 环比 −8.30%，主因是 华东 × 水产 × 社区团购 这一组柜："
            "该组合单日从 66,379 掉到 13,339（−53,040 元），贡献 −5.2pp、占总降幅 62.7%。"
            "华东其余品类渠道反而微增 2,800 元，说明不是区域性问题，是单一供给/履约环节断了。"
            "价效应为正（客单价 +1.3%），因此降的是量不是价，优先查社区团购水产的到货与开团。"
        ),
    },
    {
        "seed_key": "seed:run:orders:2026-11-09",
        "metric": "orders",
        "target_date": "2026-11-09",
        "baseline_kind": "median_4w",   # 演示另一个基线分支：近 4 周同星期中位数
        "top_n": 10,
        "conclusion": (
            "订单量用「近 4 周同星期中位数」做基线：11-09 是周一，取前 4 个周一的订单量中位数，"
            "比单点基线更抗尖刺。归因结论与 GMV 一致——降的是量。"
        ),
    },
]

SEED_REPORT_DELIVERIES = [
    {
        "channel": DeliveryChannel.FEISHU.value,
        "channel_label": "飞书群",
        "target": "经营分析晨会群",
        "actor": "admin@swingattr.io",
        "delivered_at": "2026-11-10T08:40:00Z",
        "status": "sent",
    },
    {
        "channel": DeliveryChannel.EMAIL.value,
        "channel_label": "邮件",
        "target": "ops-lead@wotian.example",
        "actor": "admin@swingattr.io",
        "delivered_at": "2026-11-10T08:41:00Z",
        "status": "sent",
    },
]


def ensure_users(db) -> None:
    for email, display_name, role in DEMO_USERS:
        if db.scalar(select(User).where(User.email == email)):
            continue
        db.add(
            User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                team="经营分析组",
            )
        )
    db.flush()


def ensure_metrics(db) -> None:
    for spec in cfg.METRICS:
        existing = db.scalar(select(MetricDef).where(MetricDef.code == spec.code))
        if existing is not None:
            continue
        db.add(
            MetricDef(
                code=spec.code,
                name=spec.name,
                unit=spec.unit,
                kind=spec.kind,
                formula_text=spec.formula_text,
                numerator=spec.numerator,
                denominator=spec.denominator,
                owner=spec.owner,
                higher_is_better=spec.higher_is_better,
                description=spec.description,
                sort_order=spec.sort_order,
            )
        )
    db.flush()


def ensure_dimensions(db) -> None:
    for dim in cfg.DIMENSIONS:
        for order, (code, name, parent) in enumerate(dim.members):
            existing = db.scalar(
                select(DimTree).where(DimTree.dimension == dim.code, DimTree.member_code == code)
            )
            if existing is not None:
                continue
            db.add(
                DimTree(
                    dimension=dim.code,
                    member_code=code,
                    member_name=name,
                    parent_code=parent,
                    level=2 if parent else 1,
                    sort_order=order,
                )
            )
    db.flush()


def ensure_facts(db) -> int:
    """按日期整批插入；已存在的日期跳过，保证幂等且不重复 5000 条。"""
    existing_days = {
        row[0]
        for row in db.execute(select(func.distinct(FactDaily.stat_date))).all()
    }
    facts, _summary = build_facts()
    created = 0
    for row in facts:
        if row["stat_date"] in existing_days:
            continue
        db.add(
            FactDaily(
                stat_date=row["stat_date"],
                city=row["city"],
                category=row["category"],
                channel=row["channel"],
                store_code=row["store_code"],
                segment=row["segment"],
                gmv=row["gmv"],
                orders=row["orders"],
                new_members=row["new_members"],
                gross_profit=row["gross_profit"],
            )
        )
        created += 1
    db.flush()
    return created


def ensure_attribution_runs(db) -> dict[int | str, int]:
    """返回 {"seed:run:gmv:2026-11-09": run_id, ...}"""
    from src.services import metric_service

    run_ids: dict[str, int] = {}
    for spec in SEED_RUNS:
        existing = db.scalar(select(AttributionRun).where(AttributionRun.seed_key == spec["seed_key"]))
        if existing is not None:
            run_ids[spec["seed_key"]] = existing.id
            continue
        metric = metric_service.get_metric(db, spec["metric"])
        result = swing_service.run_attribution(
            db,
            metric,
            spec["target_date"],
            spec["baseline_kind"],
            spec["top_n"],
            "seed@swingattr.io",
            spec["conclusion"],
            seed_key=spec["seed_key"],
        )
        run_ids[spec["seed_key"]] = result["run"]["id"]
    db.flush()
    return run_ids


def ensure_report(db, run_ids: dict[str, int]) -> None:
    seed_key = "seed:report:gmv:2026-11-09"
    if db.scalar(select(ReportIssue).where(ReportIssue.seed_key == seed_key)):
        return
    run_id = run_ids.get("seed:run:gmv:2026-11-09")
    if run_id is None:
        return
    report = report_service.create_report(
        db, run_id, SEED_RUNS[0]["conclusion"], "admin@swingattr.io"
    )
    row = db.scalar(select(ReportIssue).where(ReportIssue.id == report["id"]))
    row.seed_key = seed_key
    row.status = ReportStatus.PUBLISHED.value
    row.deliveries = SEED_REPORT_DELIVERIES
    db.flush()


def ensure_audit(db) -> None:
    entries = [
        ("seed:audit:1", "admin@swingattr.io", "admin", "auth.login", "user", "1", {"role": "admin"}),
        ("seed:audit:2", "analyst@swingattr.io", "analyst", "attribution.run", "attribution_run", "1",
         {"metric": "gmv", "target": cfg.TARGET_DATE}),
    ]
    for seed_key, email, role, action, entity, entity_id, detail in entries:
        if db.scalar(select(AuditLog).where(AuditLog.seed_key == seed_key)):
            continue
        db.add(
            AuditLog(
                actor_email=email,
                actor_role=role,
                action=action,
                entity=entity,
                entity_id=entity_id,
                detail=detail,
                layer="seed",
                ip="127.0.0.1",
                seed_key=seed_key,
            )
        )
    db.flush()


def seed_all() -> str:
    with session_scope() as db:
        ensure_users(db)
        ensure_metrics(db)
        ensure_dimensions(db)
        ensure_facts(db)
        run_ids = ensure_attribution_runs(db)
        ensure_report(db, run_ids)
        ensure_audit(db)

        metric_count = db.scalar(select(func.count()).select_from(MetricDef)) or 0
        day_count = db.scalar(select(func.count(func.distinct(FactDaily.stat_date)))) or 0
        fact_count = db.scalar(select(func.count()).select_from(FactDaily)) or 0
        run_count = (
            db.scalar(
                select(func.count()).select_from(AttributionRun).where(AttributionRun.seed_key.isnot(None))
            )
            or 0
        )
        report_count = (
            db.scalar(
                select(func.count()).select_from(ReportIssue).where(ReportIssue.seed_key.isnot(None))
            )
            or 0
        )
        user_count = db.scalar(select(func.count()).select_from(User)) or 0

    summary = (
        f"SEED_SUMMARY brand=swingattr metrics={metric_count} days={day_count} facts={fact_count} "
        f"runs={run_count} reports={report_count} users={user_count}"
    )
    print(summary, flush=True)
    return summary


if __name__ == "__main__":
    seed_all()

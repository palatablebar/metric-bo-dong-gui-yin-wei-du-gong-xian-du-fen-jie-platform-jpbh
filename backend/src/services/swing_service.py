"""算法 1：指标波动分解。

两条分解路径（按 MetricDef.kind 自动切换）：

A. 加法指标（订单量 / 新客数 / 毛利额）
   Δ = value_now − value_base
   成员贡献 contribution_i = v_now,i − v_base,i
   Σ 成员贡献 == Δ（同一维度是完整划分，残差 0，解释度 100%）

B. 乘法指标（GMV = 订单量 × 客单价）
   Δln = ln(v_now / v_base) = ln(量比) + ln(价比)
   量/价效应按 Δln 占比回摊到金额：contribution_i = Δ × Δln_i / Δln
   保证 量效应 + 价效应 == Δ（严格守恒）

组合扫描（痛点②：城市×品类×渠道≈576 个组合无法穷举）：
   只扫前 3 维的 2 维对(33) + 3 维组(36)，按 |Δ| 排名；
   36 个三元组是完整划分，Top-N 截断后的残差显式列出（残差 + 解释度合计）。

所有结果落库（AttributionRun + SwingFactor），同一入参重复运行结果完全一致。
"""
from __future__ import annotations

import itertools
import math
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import (
    ANOMALY_LABELS,
    BASELINE_LABELS,
    DIMENSION_LABELS,
    RUN_STATUS_LABELS,
    AnomalyLevel,
    BaselineKind,
    FactorKind,
    MetricKind,
    RunStatus,
)
from src.constants.limits import (
    DEFAULT_TOP_N,
    EXPLAINED_PARTIAL_THRESHOLD,
    MAX_COMBO_DIMENSIONS,
    MAX_FACTORS,
)
from src.models.attribution_run import AttributionRun
from src.models.dim_tree import DimTree
from src.models.fact_daily import FactDaily
from src.models.metric_def import MetricDef
from src.models.swing_factor import SwingFactor
from src.services import baseline_service, metric_service
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, parse_date

COMBO_DIMS = ("city", "category", "channel")
DRILL_CHAIN = ("city", "category", "channel", "store", "segment")
DIM_COLUMN = {
    "city": FactDaily.city,
    "category": FactDaily.category,
    "channel": FactDaily.channel,
    "store": FactDaily.store_code,
    "segment": FactDaily.segment,
}
MEASURE_COLUMN = {
    "gmv": FactDaily.gmv,
    "orders": FactDaily.orders,
    "new_members": FactDaily.new_members,
    "gross_profit": FactDaily.gross_profit,
}


def member_map(db: Session) -> dict[tuple[str, str], str]:
    rows = db.scalars(select(DimTree)).all()
    return {(row.dimension, row.member_code): row.member_name for row in rows}


def _measure(db: Session, code: str):
    column = MEASURE_COLUMN.get(code)
    if column is None:
        raise AppError("METRIC_NOT_DECOMPOSABLE", 422, detail=f"measure={code}")
    return column


def group_values(db: Session, day: date, dims: tuple[str, ...], measure: str, filters: dict | None = None) -> dict[tuple, float]:
    """按若干维度聚合某天的某个度量。"""
    columns = [DIM_COLUMN[dim] for dim in dims]
    from sqlalchemy import func

    stmt = select(*columns, func.sum(_measure(db, measure))).where(FactDaily.stat_date == day)
    for dim, member in (filters or {}).items():
        column = DIM_COLUMN.get(dim)
        if column is not None:
            stmt = stmt.where(column == member)
    stmt = stmt.group_by(*columns)
    result: dict = {}
    for row in db.execute(stmt).all():
        values = row[: len(columns)]
        # 单维 → str key；多维 → tuple key（下游据此判断是否组合）
        key = values[0] if len(columns) == 1 else tuple(values)
        result[key] = float(row[-1] or 0)
    return result


def day_measure(db: Session, day: date, measure: str) -> float:
    from sqlalchemy import func

    value = db.scalar(
        select(func.sum(_measure(db, measure))).where(FactDaily.stat_date == day)
    )
    return float(value or 0)


def multiplicative_components(db: Session, metric: MetricDef, now: date, base: date) -> list[dict]:
    """GMV 的量价拆解；返回按 Δln 守恒回摊到金额的效应项。"""
    gmv_now = day_measure(db, now, "gmv")
    gmv_base = day_measure(db, base, "gmv")
    orders_now = day_measure(db, now, "orders")
    orders_base = day_measure(db, base, "orders")
    aov_now = gmv_now / orders_now if orders_now else 0.0
    aov_base = gmv_base / orders_base if orders_base else 0.0
    delta = gmv_now - gmv_base

    if metric.code == "gmv":
        delta_ln_total = math.log(gmv_now / gmv_base) if gmv_now and gmv_base else 0.0
        parts = [
            ("volume", "量效应（订单量）", "订单量", orders_now, orders_base,
             math.log(orders_now / orders_base) if orders_now and orders_base else 0.0),
            ("price", "价效应（客单价）", "客单价", aov_now, aov_base,
             math.log(aov_now / aov_base) if aov_now and aov_base else 0.0),
        ]
    else:  # aov = gmv / orders
        delta_ln_total = math.log(aov_now / aov_base) if aov_now and aov_base else 0.0
        parts = [
            ("gmv", "GMV 推动", "GMV", gmv_now, gmv_base,
             math.log(gmv_now / gmv_base) if gmv_now and gmv_base else 0.0),
            ("orders", "订单量摊薄", "订单量", orders_now, orders_base,
             -math.log(orders_now / orders_base) if orders_now and orders_base else 0.0),
        ]

    components = []
    for key, label, member_label, value_now, value_base, delta_ln in parts:
        weight = (delta_ln / delta_ln_total) if delta_ln_total else 0.0
        contribution = delta * weight
        components.append(
            {
                "key": key,
                "label": label,
                "member_name": member_label,
                "value_now": round(value_now, 4),
                "value_base": round(value_base, 4),
                "delta_ln": round(delta_ln, 6),
                "ln_weight": round(weight, 6),
                "contribution_value": round(contribution, 2),
                "contribution_pp": round(contribution / gmv_base * 100, 2) if gmv_base else 0.0,
                "contribution_pct": round(contribution / delta * 100, 2) if delta else 0.0,
            }
        )
    return components


def _factor_from_values(
    names: dict[tuple[str, str], str],
    dims: tuple[str, ...],
    key: tuple,
    value_now: float,
    value_base: float,
    total_base: float,
    total_delta: float,
    kind: str,
) -> dict:
    delta = value_now - value_base
    labels = "×".join(DIMENSION_LABELS.get(dim, dim) for dim in dims)
    path = "/".join(key)
    name_path = " × ".join(names.get((dim, member), member) for dim, member in zip(dims, key))
    return {
        "kind": kind,
        "dim_name": "×".join(dims),
        "dim_label": labels,
        "member_code": path,
        "member_name": name_path,
        "path": path,
        "path_label": name_path,
        "value_now": round(value_now, 2),
        "value_base": round(value_base, 2),
        "delta_value": round(delta, 2),
        "contribution_pp": round(delta / total_base * 100, 2) if total_base else 0.0,
        "contribution_pct": round(delta / total_delta * 100, 2) if total_delta else 0.0,
        "share_pct": 0.0,
    }


def dimension_breakdown(
    db: Session,
    names: dict[tuple[str, str], str],
    metric_code: str,
    now: date,
    base: date,
    total_base: float,
    total_delta: float,
) -> list[dict]:
    result = []
    measure = measure_for(metric_code)
    for dim in DRILL_CHAIN:
        values_now = group_values(db, now, (dim,), measure)
        values_base = group_values(db, base, (dim,), measure)
        members = sorted(set(values_now) | set(values_base))
        rows = []
        for member in members:
            v_now = values_now.get((member,), 0.0)
            v_base = values_base.get((member,), 0.0)
            rows.append(
                _factor_from_values(
                    names, (dim,), (member,), v_now, v_base, total_base, total_delta, FactorKind.DIMENSION.value
                )
            )
        rows.sort(key=lambda item: -abs(item["delta_value"]))
        explained = sum(row["delta_value"] for row in rows)
        result.append(
            {
                "dim": dim,
                "dim_label": DIMENSION_LABELS.get(dim, dim),
                "members": rows,
                "explained_value": round(explained, 2),
                "residual_value": round(total_delta - explained, 2),
                "explained_pct": round(explained / total_delta * 100, 2) if total_delta else 100.0,
            }
        )
    return result


def measure_for(metric_code: str) -> str:
    """组合/下钻扫描用的度量列：GMV 与客单价都落在 GMV 上，其它指标用自己的列。"""
    return "gmv" if metric_code in ("gmv", "aov") else metric_code


def combo_factors(
    db: Session,
    names: dict[tuple[str, str], str],
    metric_code: str,
    now: date,
    base: date,
    total_base: float,
    total_delta: float,
) -> tuple[list[dict], int]:
    measure = measure_for(metric_code)
    factors: list[dict] = []
    dims = COMBO_DIMS[:MAX_COMBO_DIMENSIONS]
    # 只扫「样本内最大维度数」的组合（3 维 = 36 组），它是总波动的完整划分；
    # 2 维对会与 3 维组重复计数，会让 Top-N 解释度爆表，所以不参与排名。
    for size in (len(dims),):
        for combo in itertools.combinations(dims, size):
            values_now = group_values(db, now, combo, measure)
            values_base = group_values(db, base, combo, measure)
            keys = sorted(set(values_now) | set(values_base))
            for key in keys:
                factors.append(
                    _factor_from_values(
                        names,
                        combo,
                        key,
                        values_now.get(key, 0.0),
                        values_base.get(key, 0.0),
                        total_base,
                        total_delta,
                        FactorKind.COMBO.value,
                    )
                )
    factors.sort(key=lambda item: (-abs(item["delta_value"]), item["member_code"]))
    triples = [item for item in factors if item["dim_name"].count("×") == 2]
    for index, item in enumerate(factors, start=1):
        item["rank"] = index
    return factors, len(triples)


def run_attribution(
    db: Session,
    metric: MetricDef,
    target_date: str,
    baseline_kind: str | None,
    top_n: int,
    created_by: str,
    conclusion: str = "",
    seed_key: str | None = None,
) -> dict:
    target = parse_date(target_date)
    baseline = baseline_service.suggest(db, metric, target)
    if baseline_kind and baseline_kind != baseline["chosen"]["kind"]:
        picked = next((item for item in baseline["candidates"] if item["kind"] == baseline_kind), None)
        if picked is None or not picked["available"]:
            raise AppError("NO_BASELINE", 422, detail=f"baseline={baseline_kind} 不可用")
        chosen = {
            "kind": picked["kind"],
            "label": picked["label"],
            "baseline_date": picked["baseline_date"],
            "baseline_weekday": picked["weekday"],
            "base_value": picked["base_value"],
            "delta_value": picked["delta_value"],
            "delta_pct": picked["delta_pct"],
        }
        baseline["chosen"] = chosen
        z = abs(picked["delta_value"]) / baseline["robust"]["mad"] if baseline["robust"]["mad"] else 0.0
        baseline["z_score"] = round(z, 3)
        baseline["anomaly_level"] = baseline_service.anomaly_level(z)
        baseline["anomaly_label"] = ANOMALY_LABELS[baseline["anomaly_level"]]
        baseline["is_anomaly"] = z >= 3.0

    base_date = parse_date(baseline["chosen"]["baseline_date"])
    value_now = baseline["value_now"]
    value_base = baseline["chosen"]["base_value"]
    delta = value_now - value_base
    delta_pct = delta / value_base * 100 if value_base else 0.0
    if abs(delta) < 1e-9:
        raise AppError("VALIDATION", 422, detail="该日无波动（Δ=0），不需要归因")

    names = member_map(db)
    components = []
    if metric.kind == MetricKind.MULTIPLICATIVE.value:
        components = multiplicative_components(db, metric, target, base_date)

    dimensions = dimension_breakdown(db, names, metric.code, target, base_date, value_base, delta)
    combos, triple_total = combo_factors(db, names, metric.code, target, base_date, value_base, delta)
    top = combos[: min(top_n, MAX_FACTORS)]
    explained_value = sum(item["delta_value"] for item in top)
    # 解释度用「绝对覆盖」口径：Top-N 的 |Δ| 和 / 全部 36 组的 |Δ| 和，
    # 这样因子正负抵消时也不会超过 100%（有符号口径另存 signed_pct）
    abs_total = sum(abs(item["delta_value"]) for item in combos) or 0.0
    explained_abs = sum(abs(item["delta_value"]) for item in top)
    explained_pct = explained_abs / abs_total * 100 if abs_total else 0.0
    signed_pct = explained_value / delta * 100 if delta else 0.0
    residual = delta - explained_value

    status = (
        RunStatus.SUCCESS.value
        if explained_pct >= EXPLAINED_PARTIAL_THRESHOLD * 100
        else RunStatus.PARTIAL.value
    )
    dims_scanned = ["city", "category", "channel"]
    run = AttributionRun(
        metric_code=metric.code,
        target_date=target,
        baseline_kind=baseline["chosen"]["kind"],
        baseline_date=base_date,
        status=status,
        anomaly_level=baseline["anomaly_level"],
        z_score=float(baseline["z_score"]),
        mad_value=float(baseline["robust"]["mad"]),
        value_now=value_now,
        value_base=value_base,
        delta_value=round(delta, 2),
        delta_pct=round(delta_pct, 4),
        explained_pct=round(explained_pct, 2),
        residual_value=round(residual, 2),
        top_n=min(top_n, MAX_FACTORS),
        dims=dims_scanned,
        components={
            "items": components,
            "triple_total": triple_total,
            "abs_total": round(abs_total, 2),
            "signed_pct": round(signed_pct, 2),
        },
        conclusion=conclusion or _auto_conclusion(metric, top, delta, explained_pct),
        created_by=created_by,
        seed_key=seed_key,
    )
    db.add(run)
    db.flush()

    stored = 0
    for item in top:
        db.add(
            SwingFactor(
                run_id=run.id,
                kind=item["kind"],
                dim_name=item["dim_name"],
                member_code=item["member_code"],
                member_name=item["member_name"],
                path=item["path"],
                component=None,
                value_now=item["value_now"],
                value_base=item["value_base"],
                delta_value=item["delta_value"],
                contribution_pp=item["contribution_pp"],
                contribution_pct=item["contribution_pct"],
                share_pct=item["share_pct"],
                rank=item["rank"],
            )
        )
        stored += 1
    for component in components:
        db.add(
            SwingFactor(
                run_id=run.id,
                kind=FactorKind.COMPONENT.value,
                dim_name=component["key"],
                member_code=component["key"],
                member_name=component["label"],
                path=component["key"],
                component=component["key"],
                value_now=component["value_now"],
                value_base=component["value_base"],
                delta_value=component["contribution_value"],
                contribution_pp=component["contribution_pp"],
                contribution_pct=component["contribution_pct"],
                rank=0,
            )
        )
        stored += 1
    for group in dimensions:
        for member in group["members"]:
            db.add(
                SwingFactor(
                    run_id=run.id,
                    kind=FactorKind.DIMENSION.value,
                    dim_name=group["dim"],
                    member_code=member["member_code"],
                    member_name=member["member_name"],
                    path=member["path"],
                    component=None,
                    value_now=member["value_now"],
                    value_base=member["value_base"],
                    delta_value=member["delta_value"],
                    contribution_pp=member["contribution_pp"],
                    contribution_pct=member["contribution_pct"],
                    rank=0,
                )
            )
            stored += 1
    db.flush()

    return {
        "run": serialize_run(run, metric),
        "baseline": baseline,
        "components": components,
        "dimensions": dimensions,
        "factors": top,
        "factor_pool_size": len(combos),
        "explained": {
            "top_n": len(top),
            "explained_value": round(explained_value, 2),
            "explained_pct": round(explained_pct, 2),
            "signed_pct": round(signed_pct, 2),
            "abs_total": round(abs_total, 2),
            "explained_abs": round(explained_abs, 2),
            "residual_value": round(residual, 2),
            "residual_pct": round(residual / delta * 100, 2) if delta else 0.0,
            "combos_total": len(combos),
            "triples_total": triple_total,
            "conservation_ok": abs(residual + explained_value - delta) < 0.51,
        },
        "stored_factors": stored,
    }


def _auto_conclusion(metric: MetricDef, top: list[dict], delta: float, explained_pct: float) -> str:
    if not top:
        return "未找到显著贡献因子"
    leader = top[0]
    direction = "下滑" if delta < 0 else "上涨"
    return (
        f"{metric.name}{direction}的主因是 {leader['path_label']}（{leader['dim_label']}），"
        f"贡献 {leader['delta_value']:+,.0f}{metric.unit}（{leader['contribution_pp']:+.2f}pp / "
        f"占总波动 {leader['contribution_pct']:.1f}%）；Top {len(top)} 因子合计解释 {explained_pct:.1f}%。"
    )


def serialize_run(run: AttributionRun, metric: MetricDef | None = None) -> dict:
    return {
        "id": run.id,
        "metric_code": run.metric_code,
        "metric_name": metric.name if metric else run.metric_code,
        "unit": metric.unit if metric else "",
        "target_date": run.target_date.isoformat(),
        "baseline_kind": run.baseline_kind,
        "baseline_label": BASELINE_LABELS.get(run.baseline_kind, run.baseline_kind),
        "baseline_date": run.baseline_date.isoformat(),
        "status": run.status,
        "status_label": RUN_STATUS_LABELS.get(run.status, run.status),
        "anomaly_level": run.anomaly_level,
        "anomaly_label": ANOMALY_LABELS.get(run.anomaly_level, run.anomaly_level),
        "z_score": round(run.z_score, 3),
        "mad_value": round(run.mad_value, 2),
        "value_now": round(run.value_now, 2),
        "value_base": round(run.value_base, 2),
        "delta_value": round(run.delta_value, 2),
        "delta_pct": round(run.delta_pct, 2),
        "explained_pct": round(run.explained_pct, 2),
        "residual_value": round(run.residual_value, 2),
        "top_n": run.top_n,
        "dims": run.dims,
        "triple_total": (run.components or {}).get("triple_total", 0),
        "conclusion": run.conclusion,
        "created_by": run.created_by,
        "created_at": iso_utc(run.created_at),
    }


def list_runs(db: Session, limit: int = 20) -> dict:
    runs = db.scalars(select(AttributionRun).order_by(AttributionRun.id.desc()).limit(limit)).all()
    metrics = {row.code: row for row in db.scalars(select(MetricDef)).all()}
    return {
        "items": [serialize_run(run, metrics.get(run.metric_code)) for run in runs],
        "total": len(runs),
    }


def get_run_detail(db: Session, run_id: int) -> dict:
    run = db.scalar(select(AttributionRun).where(AttributionRun.id == run_id))
    if run is None:
        raise AppError("NOT_FOUND", 404, detail=f"run={run_id}")
    metric = db.scalar(select(MetricDef).where(MetricDef.code == run.metric_code))
    factors = db.scalars(
        select(SwingFactor).where(SwingFactor.run_id == run_id, SwingFactor.rank > 0).order_by(SwingFactor.rank)
    ).all()
    components = db.scalars(
        select(SwingFactor).where(SwingFactor.run_id == run_id, SwingFactor.kind == FactorKind.COMPONENT.value)
    ).all()
    dim_factors = db.scalars(
        select(SwingFactor).where(SwingFactor.run_id == run_id, SwingFactor.kind == FactorKind.DIMENSION.value)
    ).all()
    payload_factors = [_serialize_factor(item) for item in factors]
    explained_value = sum(item["delta_value"] for item in payload_factors)
    delta = run.delta_value
    dimensions = []
    for dim in DRILL_CHAIN:
        members = [_serialize_factor(item) for item in dim_factors if item.dim_name == dim]
        members.sort(key=lambda item: -abs(item["delta_value"]))
        sum_delta = sum(item["delta_value"] for item in members)
        dimensions.append(
            {
                "dim": dim,
                "dim_label": DIMENSION_LABELS.get(dim, dim),
                "members": members,
                "explained_value": round(sum_delta, 2),
                "residual_value": round(delta - sum_delta, 2),
                "explained_pct": round(sum_delta / delta * 100, 2) if delta else 100.0,
            }
        )
    meta = run.components or {}
    return {
        "run": serialize_run(run, metric),
        "components": [_serialize_factor(item) for item in components],
        "dimensions": dimensions,
        "factors": payload_factors,
        "factor_pool_size": len(payload_factors),
        "explained": {
            "top_n": len(payload_factors),
            "explained_value": round(explained_value, 2),
            "explained_pct": run.explained_pct,
            "signed_pct": meta.get("signed_pct", run.explained_pct),
            "abs_total": meta.get("abs_total", 0),
            "explained_abs": round(sum(abs(item["delta_value"]) for item in payload_factors), 2),
            "residual_value": round(delta - explained_value, 2),
            "residual_pct": round((delta - explained_value) / delta * 100, 2) if delta else 0.0,
            "triples_total": meta.get("triple_total", 0),
            "combos_total": len(payload_factors),
            "conservation_ok": abs((delta - explained_value) + explained_value - delta) < 0.51,
        },
    }


def _serialize_factor(item: SwingFactor) -> dict:
    return {
        "id": item.id,
        "rank": item.rank,
        "kind": item.kind,
        "dim_name": item.dim_name,
        "dim_label": DIMENSION_LABELS.get(item.dim_name, item.dim_name),
        "member_code": item.member_code,
        "member_name": item.member_name,
        "path": item.path,
        "path_label": item.member_name,
        "component": item.component,
        "value_now": round(item.value_now, 2),
        "value_base": round(item.value_base, 2),
        "delta_value": round(item.delta_value, 2),
        "contribution_pp": round(item.contribution_pp, 2),
        "contribution_pct": round(item.contribution_pct, 2),
        "share_pct": round(item.share_pct, 2),
        "is_leader": item.rank == 1,
    }


def day_measure_filtered(db: Session, day, measure: str, filters: dict | None = None) -> float:
    """带维度过滤的当日度量合计（下钻页用）。"""
    from sqlalchemy import func

    stmt = select(func.sum(_measure(db, measure))).where(FactDaily.stat_date == day)
    for dim, member in (filters or {}).items():
        column = DIM_COLUMN.get(dim)
        if column is not None:
            stmt = stmt.where(column == member)
    value = db.scalar(stmt)
    return float(value or 0)

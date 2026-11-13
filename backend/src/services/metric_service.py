"""指标口径读写 + 日序列/维度聚合（所有页面共用这一份读数口径）。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import MetricKind
from src.models.fact_daily import FactDaily
from src.models.metric_def import MetricDef
from src.utils.errors import AppError
from src.utils.timeutil import date_range, parse_date, weekday_label

FACT_COLUMNS = {
    "gmv": FactDaily.gmv,
    "orders": FactDaily.orders,
    "new_members": FactDaily.new_members,
    "gross_profit": FactDaily.gross_profit,
}
DIM_COLUMNS = {
    "city": FactDaily.city,
    "category": FactDaily.category,
    "channel": FactDaily.channel,
    "store": FactDaily.store_code,
    "segment": FactDaily.segment,
}
# 乘法指标量价拆解用的两个底表列
COMPONENT_COLUMNS = {
    "gmv": ("orders", "aov"),
    "aov": ("gmv", "orders"),
}


def list_metrics(db: Session) -> list[dict]:
    rows = db.scalars(select(MetricDef).order_by(MetricDef.sort_order, MetricDef.id)).all()
    return [serialize_metric(row) for row in rows]


def get_metric(db: Session, code: str) -> MetricDef:
    metric = db.scalar(select(MetricDef).where(MetricDef.code == code))
    if metric is None:
        raise AppError("NOT_FOUND", 404, detail=f"metric={code}")
    return metric


def serializer_metric_alias() -> None:  # pragma: no cover - 兼容命名
    return None


def serialize_metric(metric: MetricDef) -> dict:
    return {
        "id": metric.id,
        "code": metric.code,
        "name": metric.name,
        "unit": metric.unit,
        "kind": metric.kind,
        "kind_label": "加法指标" if metric.kind == MetricKind.ADDITIVE.value else "乘法指标",
        "formula_text": metric.formula_text,
        "numerator": metric.numerator,
        "denominator": metric.denominator,
        "owner": metric.owner,
        "higher_is_better": metric.higher_is_better,
        "description": metric.description,
        "decomposable": metric.code in ("gmv", "orders", "new_members", "gross_profit")
        or metric.code in COMPONENT_COLUMNS,
    }


def metric_expression(metric: MetricDef):
    """把指标口径翻成 SQL 聚合表达式；aov 这种派生指标用 SUM/SUM 表达。"""
    if metric.code in FACT_COLUMNS:
        return func.sum(FACT_COLUMNS[metric.code])
    if metric.code == "aov":
        return func.sum(FactDaily.gmv) / func.nullif(func.sum(FactDaily.orders), 0)
    raise AppError("METRIC_NOT_DECOMPOSABLE", 422, detail=f"metric={metric.code}")


def daily_series(db: Session, metric: MetricDef, end_date: str | None, days: int) -> list[dict]:
    stmt = select(
        FactDaily.stat_date,
        func.sum(FactDaily.gmv).label("gmv"),
        func.sum(FactDaily.orders).label("orders"),
        func.sum(FactDaily.new_members).label("new_members"),
        func.sum(FactDaily.gross_profit).label("gross_profit"),
    ).group_by(FactDaily.stat_date).order_by(FactDaily.stat_date)
    rows = db.execute(stmt).all()
    if not rows:
        raise AppError("NO_FACT", 422, detail="事实表为空")
    by_date = {row.stat_date: row for row in rows}
    latest = parse_date(end_date) if end_date else max(by_date)
    series = []
    for day in date_range(latest, days):
        row = by_date.get(day)
        if row is None:
            continue
        value = _metric_value(metric.code, row)
        series.append(
            {
                "date": day.isoformat(),
                "weekday": weekday_label(day),
                "value": round(value, 2),
            }
        )
    return series


def _metric_value(code: str, row) -> float:
    if code == "gmv":
        return float(row.gmv or 0)
    if code == "orders":
        return float(row.orders or 0)
    if code == "new_members":
        return float(row.new_members or 0)
    if code == "gross_profit":
        return float(row.gross_profit or 0)
    if code == "aov":
        return float(row.gmv or 0) / float(row.orders or 1)
    raise AppError("METRIC_NOT_DECOMPOSABLE", 422, detail=f"metric={code}")


def day_totals(db: Session, metric: MetricDef, day: str) -> dict:
    rows = db.execute(
        select(
            func.sum(FactDaily.gmv),
            func.sum(FactDaily.orders),
            func.sum(FactDaily.new_members),
            func.sum(FactDaily.gross_profit),
            func.count(FactDaily.id),
        ).where(FactDaily.stat_date == parse_date(day))
    ).one()
    if not rows[4]:
        raise AppError("NO_FACT", 422, detail=f"date={day}")
    payload = {
        "gmv": float(rows[0] or 0),
        "orders": float(rows[1] or 0),
        "new_members": float(rows[2] or 0),
        "gross_profit": float(rows[3] or 0),
        "rows": int(rows[4]),
    }
    payload["aov"] = payload["gmv"] / payload["orders"] if payload["orders"] else 0.0
    return {
        "date": day,
        "weekday": weekday_label(parse_date(day)),
        "rows": payload["rows"],
        "values": {key: round(value, 2) for key, value in payload.items() if key != "rows"},
    }


def load_dim_values(db: Session, day: str, dimension: str, metric_code: str) -> dict[str, float]:
    """按单个维度把某天的指标值聚合成 {成员: 值}。"""
    column = DIM_COLUMNS.get(dimension)
    if column is None:
        raise AppError("VALIDATION", 422, detail=f"dimension={dimension}")
    metric = get_metric(db, metric_code)
    rows = db.execute(
        select(column, func.sum(FactDaily.gmv), func.sum(FactDaily.orders),
               func.sum(FactDaily.new_members), func.sum(FactDaily.gross_profit))
        .where(FactDaily.stat_date == parse_date(day))
        .group_by(column)
    ).all()
    result: dict[str, float] = {}
    for member, gmv, orders, new_members, gross_profit in rows:
        if metric.code == "gmv":
            value = float(gmv or 0)
        elif metric.code == "orders":
            value = float(orders or 0)
        elif metric.code == "new_members":
            value = float(new_members or 0)
        elif metric.code == "gross_profit":
            value = float(gross_profit or 0)
        else:
            value = float(gmv or 0) / float(orders or 1)
        result[member] = value
    return result

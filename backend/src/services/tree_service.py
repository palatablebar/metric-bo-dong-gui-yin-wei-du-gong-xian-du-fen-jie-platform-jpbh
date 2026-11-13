"""维度树与逐层下钻：沿 city → category → channel → store → segment 逐层收窄。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import DIMENSION_LABELS
from src.models.dim_tree import DimTree
from src.utils.errors import AppError
from src.utils.timeutil import parse_date
from src.services import swing_service


def load_dimensions(db: Session) -> list[dict]:
    rows = db.scalars(select(DimTree).order_by(DimTree.dimension, DimTree.sort_order, DimTree.id)).all()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.dimension, []).append(
            {
                "code": row.member_code,
                "name": row.member_name,
                "parent_code": row.parent_code,
                "level": row.level,
            }
        )
    order = ["city", "category", "channel", "store", "segment"]
    return [
        {
            "code": dim,
            "label": DIMENSION_LABELS.get(dim, dim),
            "members": grouped.get(dim, []),
            "member_count": len(grouped.get(dim, [])),
        }
        for dim in order
        if dim in grouped
    ]


def drilldown(db: Session, run_row, path: dict[str, str]) -> dict:
    """给定归因批次与已选路径，返回下一个维度的子成员贡献。"""
    chain = swing_service.DRILL_CHAIN
    filters: dict[str, str] = {}
    next_dim = chain[0]
    for dim in chain:
        if dim in path and path[dim]:
            filters[dim] = path[dim]
            continue
        next_dim = dim
        break
    else:
        next_dim = ""

    base_date = run_row.baseline_date
    target_date = run_row.target_date
    measure = swing_service.measure_for(run_row.metric_code)
    names = swing_service.member_map(db)

    values_now = swing_service.group_values(db, target_date, (next_dim,) if next_dim else chain[:1], measure, filters)
    values_base = swing_service.group_values(db, base_date, (next_dim,) if next_dim else chain[:1], measure, filters)
    total_now = swing_service.day_measure_filtered(db, target_date, measure, filters)
    total_base = swing_service.day_measure_filtered(db, base_date, measure, filters)
    total_delta = total_now - total_base

    children = []
    keys = sorted(set(values_now) | set(values_base))
    for key in keys:
        member = key[0] if isinstance(key, tuple) else key
        v_now = values_now.get(key, 0.0)
        v_base = values_base.get(key, 0.0)
        delta = v_now - v_base
        children.append(
            {
                "dim": next_dim,
                "dim_label": DIMENSION_LABELS.get(next_dim, next_dim),
                "member_code": member,
                "member_name": names.get((next_dim, member), member),
                "value_now": round(v_now, 2),
                "value_base": round(v_base, 2),
                "delta_value": round(delta, 2),
                "contribution_pp": round(delta / total_base * 100, 2) if total_base else 0.0,
                "contribution_pct": round(delta / total_delta * 100, 2) if total_delta else 0.0,
                "share_of_parent": round(delta / total_delta * 100, 2) if total_delta else 0.0,
                "is_leaf": next_dim == chain[-1],
            }
        )
    children.sort(key=lambda item: -abs(item["delta_value"]))
    if next_dim == "store":
        parents = {row.member_code: row.parent_code for row in db.scalars(select(DimTree).where(DimTree.dimension == "store")).all()}
        for child in children:
            child["parent_code"] = parents.get(child["member_code"])

    return {
        "run_id": run_row.id,
        "target_date": target_date.isoformat(),
        "baseline_date": base_date.isoformat(),
        "metric_code": run_row.metric_code,
        "path": filters,
        "path_label": " / ".join(
            names.get((dim, member), member) for dim, member in filters.items()
        ) or "全部",
        "next_dim": next_dim,
        "next_dim_label": DIMENSION_LABELS.get(next_dim, next_dim) if next_dim else "已到叶子",
        "chain": list(chain),
        "value_now": round(total_now, 2),
        "value_base": round(total_base, 2),
        "delta_value": round(total_delta, 2),
        "delta_pct": round(total_delta / total_base * 100, 2) if total_base else 0.0,
        "children": children,
        "child_count": len(children),
    }

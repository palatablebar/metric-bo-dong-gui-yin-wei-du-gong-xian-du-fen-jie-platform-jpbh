"""算法 2：基线选择与节假日校正。

  MAD      = median(|x − median(x)|)      近 4 周同星期序列的稳健离散
  Δ        = 本期 − 所选基线
  z        = |Δ| / MAD                    > 3 判异常，>= 5 升级重大
  level    = normal / warning / critical

候选基线（都返回，未选中的给出不可用原因）：
  prev_day        上一日（环比）—— 会被周末/工作日节律污染
  same_weekday    同星期（周环比）—— 默认首选，剔除周内节律
  median_4w       近 4 周同星期中位数 —— 抗单点尖刺
  holiday_shift   节假日位移 —— 命中节假日日历且能找到上一个同类节点时才可用

选基线的理由必须能讲清楚（输出 reasons 列表），这是「结论不成文」痛点的解药。
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from src.constants.enums import ANOMALY_LABELS, BASELINE_LABELS, AnomalyLevel, BaselineKind
from src.constants.limits import (
    ANOMALY_CRITICAL_THRESHOLD,
    ANOMALY_MAD_THRESHOLD,
    HOLIDAY_SHIFT_WINDOW_DAYS,
    MIN_BASELINE_POINTS,
)
from src.models.metric_def import MetricDef
from src.services import metric_service
from src.utils.errors import AppError
from src.utils.timeutil import mad as compute_mad
from src.utils.timeutil import median as compute_median
from src.utils.timeutil import parse_date, weekday_label
from scripts.demo_config import HOLIDAYS, HOLIDAY_SHIFT_PAIRS

LOOKBACK_DAYS = 35


def series_map(db: Session, metric: MetricDef, end_date: date) -> dict[date, float]:
    series = metric_service.daily_series(db, metric, end_date.isoformat(), LOOKBACK_DAYS)
    return {parse_date(point["date"]): point["value"] for point in series}


def anomaly_level(z_score: float) -> str:
    if abs(z_score) >= ANOMALY_CRITICAL_THRESHOLD:
        return AnomalyLevel.CRITICAL.value
    if abs(z_score) >= ANOMALY_MAD_THRESHOLD:
        return AnomalyLevel.WARNING.value
    return AnomalyLevel.NORMAL.value


def suggest(db: Session, metric: MetricDef, target: date) -> dict:
    values = series_map(db, metric, target)
    if target not in values:
        raise AppError("NO_FACT", 422, detail=f"date={target.isoformat()}")
    value_now = values[target]

    same_weekday_points = []
    for weeks in range(1, 5):
        day = target - timedelta(days=7 * weeks)
        if day in values:
            same_weekday_points.append((day, values[day]))
    if len(same_weekday_points) < MIN_BASELINE_POINTS:
        raise AppError(
            "NO_BASELINE",
            422,
            detail=f"同星期历史点只有 {len(same_weekday_points)} 个，至少需要 {MIN_BASELINE_POINTS} 个",
        )
    weekday_values = [value for _day, value in same_weekday_points]
    weekday_median = compute_median(weekday_values)
    weekday_mad = compute_mad(weekday_values)

    prev_day = target - timedelta(days=1)
    recent_day = same_weekday_points[0][0]
    holiday_name = _holiday_name(target)
    shift_target = _holiday_shift_target(target)
    shift_name = _holiday_name(shift_target) if shift_target else None

    candidates: list[dict] = []

    def add(kind: str, base_date: date | None, base_value: float | None, note: str, extra: dict | None = None) -> None:
        payload = {
            "kind": kind,
            "label": BASELINE_LABELS[kind],
            "baseline_date": base_date.isoformat() if base_date else None,
            "weekday": weekday_label(base_date) if base_date else None,
            "base_value": round(base_value, 2) if base_value is not None else None,
            "available": base_value is not None,
            "note": note,
        }
        if base_value is not None:
            delta = value_now - base_value
            payload["delta_value"] = round(delta, 2)
            payload["delta_pct"] = round(delta / base_value * 100, 2) if base_value else 0.0
            payload["z_score"] = round(abs(delta) / weekday_mad, 3) if weekday_mad else 0.0
        if extra:
            payload.update(extra)
        candidates.append(payload)

    prev_value = values.get(prev_day)
    add(
        BaselineKind.PREV_DAY.value,
        prev_day if prev_value is not None else None,
        prev_value,
        "上一日；周末与工作日节律不同，日环比容易被星期效应污染"
        if prev_value is not None
        else "上一日无数据",
    )
    add(
        BaselineKind.SAME_WEEKDAY.value,
        recent_day,
        values[recent_day],
        f"{weekday_label(target)}对{weekday_label(recent_day)}，剔除周内节律；稳健异常也按这条序列算",
    )
    add(
        BaselineKind.MEDIAN_4W.value,
        recent_day,
        weekday_median,
        f"近 {len(weekday_values)} 个同星期值的中位数，抗单点尖刺",
        {"points": [{"date": day.isoformat(), "value": round(value, 2)} for day, value in same_weekday_points],
         "median": round(weekday_median, 2), "mad": round(weekday_mad, 2)},
    )
    shift_value = values.get(shift_target) if shift_target else None
    add(
        BaselineKind.HOLIDAY_SHIFT.value,
        shift_target if shift_value is not None else None,
        shift_value,
        f"节假日位移：目标日锚定「{holiday_name}」，对齐到上一个同类节点「{shift_name}」"
        if shift_target and shift_value is not None
        else ("目标日不在节假日日历里，位移基线不适用" if not shift_target else "上一同类节点无数据"),
        {"holiday_name": holiday_name, "shift_name": shift_name} if shift_target else {},
    )

    chosen_kind = _choose_baseline(
        target=target,
        holiday_name=holiday_name,
        shift_available=shift_value is not None,
        prev_value=prev_value,
        weekday_value=values[recent_day],
    )
    chosen = next(item for item in candidates if item["kind"] == chosen_kind)
    delta = value_now - chosen["base_value"]
    z_score = abs(delta) / weekday_mad if weekday_mad else 0.0
    level = anomaly_level(z_score)
    reasons = _reasons(
        target=target,
        holiday_name=holiday_name,
        shift_available=shift_value is not None,
        prev_value=prev_value,
        weekday_value=values[recent_day],
        weekday_mad=weekday_mad,
        chosen_kind=chosen_kind,
        z_score=z_score,
    )

    return {
        "metric": metric_service.serialize_metric(metric),
        "target_date": target.isoformat(),
        "target_weekday": weekday_label(target),
        "value_now": round(value_now, 2),
        "candidates": candidates,
        "chosen": {
            "kind": chosen_kind,
            "label": BASELINE_LABELS[chosen_kind],
            "baseline_date": chosen["baseline_date"],
            "baseline_weekday": chosen["weekday"],
            "base_value": chosen["base_value"],
            "delta_value": round(delta, 2),
            "delta_pct": round(delta / chosen["base_value"] * 100, 2) if chosen["base_value"] else 0.0,
        },
        "robust": {
            "points": len(weekday_values),
            "median": round(weekday_median, 2),
            "mad": round(weekday_mad, 2),
            "delta_over_mad": round(z_score, 4),
            "threshold": ANOMALY_MAD_THRESHOLD,
            "critical_threshold": ANOMALY_CRITICAL_THRESHOLD,
        },
        "z_score": round(z_score, 3),
        "anomaly_level": level,
        "anomaly_label": ANOMALY_LABELS[level],
        "is_anomaly": abs(z_score) >= ANOMALY_MAD_THRESHOLD,
        "holiday": {
            "is_holiday": holiday_name is not None,
            "name": holiday_name,
            "shift_target": shift_target.isoformat() if shift_target else None,
            "shift_name": shift_name,
        },
        "reasons": reasons,
    }


def _holiday_name(day: date) -> str | None:
    return HOLIDAYS.get(day.isoformat())


def _holiday_shift_target(day: date) -> date | None:
    for offset in range(-HOLIDAY_SHIFT_WINDOW_DAYS, HOLIDAY_SHIFT_WINDOW_DAYS + 1):
        text = (day + timedelta(days=offset)).isoformat()
        if text in HOLIDAY_SHIFT_PAIRS:
            return parse_date(HOLIDAY_SHIFT_PAIRS[text])
    return None


def _choose_baseline(
    target: date,
    holiday_name: str | None,
    shift_available: bool,
    prev_value: float | None,
    weekday_value: float,
) -> str:
    if shift_available and holiday_name:
        return BaselineKind.HOLIDAY_SHIFT.value
    if prev_value:
        gap = abs(prev_value - weekday_value) / weekday_value if weekday_value else 0
        if gap < 0.03:
            return BaselineKind.PREV_DAY.value
    if target.weekday() == 0 and prev_value:
        # 周一 vs 周日：周末 GMV 结构性更高，日环比不可用
        return BaselineKind.SAME_WEEKDAY.value
    return BaselineKind.SAME_WEEKDAY.value


def _reasons(
    target: date,
    holiday_name: str | None,
    shift_available: bool,
    prev_value: float | None,
    weekday_value: float,
    weekday_mad: float,
    chosen_kind: str,
    z_score: float,
) -> list[str]:
    reasons: list[str] = []
    if chosen_kind == BaselineKind.HOLIDAY_SHIFT.value:
        reasons.append(f"目标日锚定节假日「{holiday_name}」，与上一个同类节点做位移对齐，比自然日更可比")
    elif chosen_kind == BaselineKind.SAME_WEEKDAY.value:
        if target.weekday() == 0 and prev_value:
            reasons.append(
                f"目标日是{weekday_label(target)}，上一日{weekday_label(target - timedelta(days=1))}属于周末，"
                f"周末 GMV 结构性偏高（{prev_value:,.0f} vs 同星期 {weekday_value:,.0f}），日环比会把周末效应算进波动"
            )
        reasons.append("同星期对齐可剔除周内节律（周一普遍低于周五/周六），是默认首选基线")
    elif chosen_kind == BaselineKind.PREV_DAY.value:
        reasons.append("上一日与同星期基线差异 < 3%，日环比可信且更贴近运营直觉")
    reasons.append(f"稳健离散 MAD={weekday_mad:,.0f}（近 4 周同星期序列的中位绝对偏差），用它做分母抵抗单点尖刺")
    if abs(z_score) >= ANOMALY_CRITICAL_THRESHOLD:
        reasons.append(f"|Δ|/MAD = {z_score:.2f} ≥ {ANOMALY_CRITICAL_THRESHOLD}，判为重大异常")
    elif abs(z_score) >= ANOMALY_MAD_THRESHOLD:
        reasons.append(f"|Δ|/MAD = {z_score:.2f} ≥ {ANOMALY_MAD_THRESHOLD}，判为异常·关注")
    else:
        reasons.append(f"|Δ|/MAD = {z_score:.2f} < {ANOMALY_MAD_THRESHOLD}，波动在正常范围内")
    return reasons

"""时间/数值工具：日期序列、格式化和百分比口径。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds") + "Z"


def parse_date(text: str) -> date:
    return date.fromisoformat(text)


def date_range(end: date, days: int) -> list[date]:
    return [end - timedelta(days=offset) for offset in reversed(range(days))]


def weekday_label(day: date) -> str:
    return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()]


def fmt_amount(value: float | int) -> str:
    return f"{round(value):,}"


def fmt_pct(value: float, digits: int = 2) -> str:
    """百分比文案：始终带符号，保留 digits 位。"""
    return f"{value:+.{digits}f}%"


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def mad(values: list[float]) -> float:
    """中位数绝对偏差 MAD = median(|x - median(x)|)。"""
    if not values:
        return 0.0
    center = median(values)
    return median([abs(value - center) for value in values])

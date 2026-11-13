"""确定性日事实生成器：把每日总量按维度权重精确摊到 5000 条明细。

为什么不用随机数：seed 必须幂等且数值可复现（Lead 会连跑两次比对 SEED_SUMMARY，
TESTING 里要写死 −8.3% / z=4.1 / −5.2pp / 62.7%）。这里全部用整数权重 + 最大余额法，
每个维度的当日总量严格等于设计值。

目标日 2026-11-09 的三组变化（合计精确闭合到 −84,660）：
  组合 华东×水产×社区团购 : −53,040（−5.2pp / 62.7%）
  华东其余柜组             : +2,800（其它品类渠道微增，所以「华东」单维降幅小于组合）
  华北 + 华南其余           : 差额（−34,420）
"""
from __future__ import annotations

import math
from datetime import date

from scripts.demo_config import (
    BASE_GMV,
    BASE_ORDERS,
    CATEGORY_MEMBERS,
    CATEGORY_WEIGHT,
    CHANNEL_MEMBERS,
    CHANNEL_WEIGHT,
    CITY_MEMBERS,
    CITY_WEIGHT,
    COMBO_CATEGORY,
    COMBO_CHANNEL,
    COMBO_CITY,
    COMBO_DELTA,
    COMBO_ORDER_RATIO,
    DAYS,
    EAST_OTHER_DELTA,
    EAST_OTHER_ORDER_RATIO,
    SEGMENT_MEMBERS,
    SEGMENT_WEIGHT,
    STORE_MEMBERS,
    STORE_WEIGHT,
    TARGET_DATE,
    TARGET_GMV,
    TARGET_ORDERS,
    date_series,
    day_target_gmv,
    day_target_orders,
    rows_for_day,
)

FACT_METRICS = ("gmv", "orders", "new_members", "gross_profit")
GROSS_MARGIN = 0.225      # 毛利率 22.5%
NEW_MEMBER_RATE = 0.09    # 新客占订单量 9%


def allocate(total: int, weights: list[int]) -> list[int]:
    """最大余额法：把整数 total 按整数权重分摊，保证求和严格等于 total。"""
    if not weights:
        return []
    total_weight = sum(weights)
    if total_weight <= 0:
        base = total // len(weights)
        out = [base] * len(weights)
        out[0] += total - base * len(weights)
        return out
    raw = [total * weight / total_weight for weight in weights]
    floors = [int(math.floor(value)) for value in raw]
    remainder = total - sum(floors)
    order = sorted(range(len(weights)), key=lambda index: (-(raw[index] - floors[index]), index))
    for index in order[:remainder]:
        floors[index] += 1
    return floors


def _row_weight(city: str, category: str, channel: str, store: str, segment: str, jitter_seed: int) -> int:
    jitter = 100 + (jitter_seed * 37) % 21 - 10
    return (
        CITY_WEIGHT[city]
        * CATEGORY_WEIGHT[category]
        * CHANNEL_WEIGHT[channel]
        * STORE_WEIGHT[store]
        * SEGMENT_WEIGHT[segment]
        * jitter
    )


def _row_order_weight(city: str, category: str, channel: str, store: str, segment: str, jitter_seed: int) -> int:
    # 订单量权重与金额权重形状相同但抖动不同 → 每条明细的客单价有差异
    jitter = 100 + (jitter_seed * 53 + 7) % 17 - 8
    segment_bias = 130 if segment == "new" else 100
    return (
        CITY_WEIGHT[city]
        * CATEGORY_WEIGHT[category]
        * CHANNEL_WEIGHT[channel]
        * STORE_WEIGHT[store]
        * segment_bias
        * jitter
    )


def _skeleton(day_index: int, day: date) -> list[dict]:
    rows: list[dict] = []
    count = rows_for_day(day_index)
    for index in range(count):
        combo = index % 36
        city = CITY_MEMBERS[combo // 12]
        category = CATEGORY_MEMBERS[(combo % 12) // 3]
        channel = CHANNEL_MEMBERS[combo % 3]
        stores = STORE_MEMBERS[city]
        store = stores[(index // 36) % len(stores)]
        segment = SEGMENT_MEMBERS[(index // 36 + index) % 2]
        rows.append(
            {
                "stat_date": day,
                "city": city,
                "category": category,
                "channel": channel,
                "store_code": store,
                "segment": segment,
                "gmv": 0,
                "orders": 0,
                "new_members": 0,
                "gross_profit": 0,
                "_gw": _row_weight(city, category, channel, store, segment, index),
                "_ow": _row_order_weight(city, category, channel, store, segment, index),
            }
        )
    return rows


def _in_combo(row: dict) -> bool:
    return (
        row["city"] == COMBO_CITY
        and row["category"] == COMBO_CATEGORY
        and row["channel"] == COMBO_CHANNEL
    )


def _in_east_other(row: dict) -> bool:
    return row["city"] == COMBO_CITY and not _in_combo(row)


def _fill_group(rows: list[dict], gmv_total: int, orders_total: int) -> None:
    gmv_values = allocate(gmv_total, [row["_gw"] for row in rows])
    order_values = allocate(orders_total, [row["_ow"] for row in rows])
    for row, gmv, orders in zip(rows, gmv_values, order_values):
        row["gmv"] = gmv
        row["orders"] = orders


def _finish_day(rows: list[dict]) -> None:
    """补齐派生列：毛利、新客（按各自权重精确分摊到当日总量）。"""
    gmv_total = sum(row["gmv"] for row in rows)
    order_total = sum(row["orders"] for row in rows)
    profit_values = allocate(round(gmv_total * GROSS_MARGIN), [row["_gw"] for row in rows])
    member_values = allocate(round(order_total * NEW_MEMBER_RATE), [row["_ow"] for row in rows])
    for row, profit, members in zip(rows, profit_values, member_values):
        row["gross_profit"] = profit
        row["new_members"] = members


def build_facts() -> tuple[list[dict], dict]:
    """返回 (5000 条明细, 目标日摘要)。整体确定性，不依赖随机数或时间。"""
    days = date_series()
    facts: list[dict] = []
    base_rows: list[dict] = []
    base_totals: dict[str, int] = {}

    for day_index, day in enumerate(days):
        rows = _skeleton(day_index, day)
        if day.isoformat() == TARGET_DATE:
            # 目标日留到最后用三组绝对变化精确闭合
            base_rows = rows
            continue
        _fill_group(rows, day_target_gmv(day), day_target_orders(day))
        _finish_day(rows)
        facts.extend(rows)
        if day.isoformat() == "2026-11-02":
            base_totals = {
                "gmv": sum(row["gmv"] for row in rows),
                "orders": sum(row["orders"] for row in rows),
                "combo_gmv": sum(row["gmv"] for row in rows if _in_combo(row)),
                "combo_orders": sum(row["orders"] for row in rows if _in_combo(row)),
                "east_other_gmv": sum(row["gmv"] for row in rows if _in_east_other(row)),
                "east_other_orders": sum(row["orders"] for row in rows if _in_east_other(row)),
            }

    target_day = date.fromisoformat(TARGET_DATE)
    combo_target = base_totals["combo_gmv"] + COMBO_DELTA
    east_other_target = base_totals["east_other_gmv"] + EAST_OTHER_DELTA
    rest_target = TARGET_GMV - combo_target - east_other_target
    combo_order_target = round(base_totals["combo_orders"] * COMBO_ORDER_RATIO)
    east_other_order_target = round(base_totals["east_other_orders"] * EAST_OTHER_ORDER_RATIO)
    rest_order_target = TARGET_ORDERS - combo_order_target - east_other_order_target

    combo_rows = [row for row in base_rows if _in_combo(row)]
    east_other_rows = [row for row in base_rows if _in_east_other(row)]
    rest_rows = [row for row in base_rows if row["city"] != COMBO_CITY]
    _fill_group(combo_rows, combo_target, combo_order_target)
    _fill_group(east_other_rows, east_other_target, east_other_order_target)
    _fill_group(rest_rows, rest_target, rest_order_target)
    _finish_day(base_rows)
    facts.extend(base_rows)

    assert sum(1 for _ in facts) == 5000, f"明细条数应为 5000，实际 {len(facts)}"
    assert sum(row["gmv"] for row in base_rows) == TARGET_GMV
    assert sum(row["orders"] for row in base_rows) == TARGET_ORDERS

    summary = {
        "target_date": target_day,
        "target_gmv": TARGET_GMV,
        "base_gmv": base_totals["gmv"],
        "target_orders": TARGET_ORDERS,
        "base_orders": base_totals["orders"],
        "combo_gmv_now": combo_target,
        "combo_gmv_base": base_totals["combo_gmv"],
        "combo_delta": COMBO_DELTA,
        "east_other_target": east_other_target,
        "rest_target": rest_target,
        "target_rows": len(base_rows),
    }
    return facts, summary


if __name__ == "__main__":
    data, info = build_facts()
    print("facts", len(data))
    for key, value in info.items():
        print(" ", key, value)
    by_date: dict[str, int] = {}
    for row in data:
        by_date[row["stat_date"].isoformat()] = by_date.get(row["stat_date"].isoformat(), 0) + row["gmv"]
    print("  days", len(by_date))

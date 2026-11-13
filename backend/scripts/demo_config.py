"""seed 演示配置：客户场景、维度、指标、30 天总量与权重。

数值不是随手写的，它们被主流程验收锁死：
  2026-11-09（周一）GMV = 935,340；基线 = 2026-11-02（周环比同星期对齐）= 1,020,000
  Δ = −84,660 → 环比 −8.30%
  MAD（近 4 个周一 968,700 / 970,000 / 1,010,000 / 1,020,000 的稳健离散）= 20,650
  z = 84,660 / 20,650 = 4.0998 → 4.1（异常）
  组合 华东 × 水产 × 社区团购：Δ = −53,040 → 折 −5.2pp（占基线 1,020,000 的 5.2%）
  该组合占总降幅 53,040 / 84,660 = 62.65% → 62.7%
  订单量 11-02 = 8,000 → 11-09 = 7,240（−9.50%）；客单价 127.50 → 129.19（+1.3%）
  GMV 对数分解：ln(0.905) + ln(1.01325) = ln(0.91699) → −8.3%，量效应为主
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

TARGET_DATE = "2026-11-09"
DAYS = 30
FIRST_DATE = date(2026, 10, 11)          # 到 2026-11-09 正好 30 天
TARGET_GMV = 935_340                      # −8.30% vs 1,020,000
BASE_GMV = 1_020_000
TARGET_ORDERS = 7_240
BASE_ORDERS = 8_000

# 目标组合：三线城市 × 水产 × 社区团购
COMBO_CITY = "east"
COMBO_CATEGORY = "seafood"
COMBO_CHANNEL = "group"

# 11-09 三组相对基线的绝对变化（合计 = −84,660，精确闭合）
COMBO_DELTA = -53_040
EAST_OTHER_DELTA = +2_800
# 余下 = TARGET_GMV - BASE_GMV - COMBO_DELTA - EAST_OTHER_DELTA = −34,420（脚本内断言）

# 目标组合的订单量相对基线的比例（供给中断：社区团购水产几乎停摆）
COMBO_ORDER_RATIO = 0.38
EAST_OTHER_ORDER_RATIO = 1.015


@dataclass(frozen=True)
class MetricSpec:
    code: str
    name: str
    unit: str
    kind: str            # additive | multiplicative
    formula_text: str
    numerator: str | None
    denominator: str | None
    owner: str
    higher_is_better: bool
    description: str
    sort_order: int


METRICS: list[MetricSpec] = [
    MetricSpec("gmv", "GMV", "元", "multiplicative", "GMV = 订单量 × 客单价",
               "orders", "aov", "林清河", True,
               "每日成交总额，晨会第一眼看的就是它；可按量价拆分", 0),
    MetricSpec("orders", "订单量", "单", "additive", "订单量 = Σ 各维度成员订单数",
               None, None, "林清河", True,
               "加法指标，可直接按维度成员求和分解", 1),
    MetricSpec("aov", "客单价", "元", "multiplicative", "客单价 = GMV ÷ 订单量",
               "gmv", "orders", "周到", True,
               "派生指标，不单独落库；用于 GMV 的量价拆分", 2),
    MetricSpec("new_members", "新客数", "人", "additive", "新客数 = Σ 首次下单会员数",
               None, None, "苏未", True,
               "拉新口径，与 GMV 一起看才知道是拉新还是复购掉了", 3),
    MetricSpec("gross_profit", "毛利额", "元", "additive", "毛利额 = GMV − 成本",
               None, None, "郑向南", True,
               "加法指标，用来复核 GMV 下滑是否被促销让价抵消", 4),
]

FACT_METRIC_COLUMNS = {
    "gmv": "gmv",
    "orders": "orders",
    "new_members": "new_members",
    "gross_profit": "gross_profit",
}


@dataclass(frozen=True)
class DimensionSpec:
    code: str
    name: str
    members: tuple[tuple[str, str, str | None], ...]   # (code, name, parent_code)

    def member_name(self, member_code: str) -> str:
        for code, name, _parent in self.members:
            if code == member_code:
                return name
        return member_code


DIMENSIONS: list[DimensionSpec] = [
    DimensionSpec("city", "城市", (
        ("east", "华东", None),
        ("north", "华北", None),
        ("south", "华南", None),
    )),
    DimensionSpec("category", "品类", (
        ("seafood", "水产", None),
        ("veggie", "蔬果", None),
        ("meat", "肉禽", None),
        ("grain", "粮油", None),
    )),
    DimensionSpec("channel", "渠道", (
        ("group", "社区团购", None),
        ("front", "前置仓", None),
        ("store", "门店自提", None),
    )),
    DimensionSpec("store", "门店", (
        ("st_east_1", "华东·江湾店", "east"),
        ("st_east_2", "华东·五角场店", "east"),
        ("st_east_3", "华东·虹桥店", "east"),
        ("st_east_4", "华东·张江店", "east"),
        ("st_north_1", "华北·望京店", "north"),
        ("st_north_2", "华北·亦庄店", "north"),
        ("st_south_1", "华南·天河店", "south"),
        ("st_south_2", "华南·南山店", "south"),
    )),
    DimensionSpec("segment", "客群", (
        ("new", "新客", None),
        ("old", "老客", None),
    )),
]

CITY_MEMBERS = ("east", "north", "south")
CATEGORY_MEMBERS = ("seafood", "veggie", "meat", "grain")
CHANNEL_MEMBERS = ("group", "front", "store")
STORE_MEMBERS = {
    "east": ("st_east_1", "st_east_2", "st_east_3", "st_east_4"),
    "north": ("st_north_1", "st_north_2"),
    "south": ("st_south_1", "st_south_2"),
}
SEGMENT_MEMBERS = ("new", "old")

# 权重（整数，用于最大余额法精确分配当日总量）
CITY_WEIGHT = {"east": 46, "north": 30, "south": 24}
CATEGORY_WEIGHT = {"seafood": 34, "veggie": 28, "meat": 22, "grain": 16}
CHANNEL_WEIGHT = {"group": 42, "front": 33, "store": 25}
STORE_WEIGHT = {
    "st_east_1": 11, "st_east_2": 12, "st_east_3": 10, "st_east_4": 13,
    "st_north_1": 12, "st_north_2": 10,
    "st_south_1": 13, "st_south_2": 11,
}
SEGMENT_WEIGHT = {"new": 30, "old": 70}

# 节假日日历（2026 年秋）：用于「节假日位移对齐」基线
# 13 位为周末位移型节日（如调休），这里给营养节/双十一预热两个业务节点
HOLIDAYS = {
    "2026-10-17": "秋季会员日",
    "2026-11-01": "双十一预热首日",
    "2026-11-11": "双十一",
}
# 位移映射：节日当天 vs 上一个同类节日（用于节假日对齐基线）
HOLIDAY_SHIFT_PAIRS = {
    "2026-11-01": "2026-10-17",
}

# 每日行数：20 天 167 行 + 10 天 166 行 = 5000 行明细
ROWS_PER_DAY_DEFAULT = 167
ROWS_PER_DAY_TAIL = 166
ROWS_TAIL_FROM = 20


def rows_for_day(day_index: int) -> int:
    return ROWS_PER_DAY_DEFAULT if day_index < ROWS_TAIL_FROM else ROWS_PER_DAY_TAIL


WEEKDAY_GMV = {0: 1_000_000, 1: 960_000, 2: 975_000, 3: 990_000, 4: 1_120_000, 5: 1_240_000, 6: 1_180_000}
# 覆盖：近 4 个周一与目标日（保证 MAD / z 精确）
MONDAY_OVERRIDES = {
    "2026-10-12": 968_700,
    "2026-10-19": 970_000,
    "2026-10-26": 1_010_000,
    "2026-11-02": BASE_GMV,
    TARGET_DATE: TARGET_GMV,
}


def date_series() -> list[date]:
    return [FIRST_DATE + timedelta(days=offset) for offset in range(DAYS)]


def day_target_gmv(day: date) -> int:
    text = day.isoformat()
    if text in MONDAY_OVERRIDES:
        return MONDAY_OVERRIDES[text]
    base = WEEKDAY_GMV[day.weekday()]
    noise = ((day.toordinal() * 7919) % 41 - 20) * 500
    return base + noise


def day_target_orders(day: date) -> int:
    """订单量与 GMV 同形，但目标日按验收值写死（8,000 → 7,240）。"""
    if day.isoformat() == TARGET_DATE:
        return TARGET_ORDERS
    if day.isoformat() == "2026-11-02":
        return BASE_ORDERS
    return max(1, round(day_target_gmv(day) / 127.5))

"""共享枚举（后端唯一定义处）。前端副本：frontend/src/constants/enums.ts"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"          # 分析负责人：指标定义 / 归因规则 / 分发
    ANALYST = "analyst"      # 分析师：跑归因、确认异常、写结论
    EXEC = "exec"            # 管理层只读日报


class MetricKind(StrEnum):
    """加法指标可按成员求和分解；乘法指标（GMV=量×价）走对数分解。"""

    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"


class MetricUnit(StrEnum):
    CNY = "元"
    ORDER = "单"
    PERSON = "人"


class BaselineKind(StrEnum):
    PREV_DAY = "prev_day"              # 环比（上一日）
    SAME_WEEKDAY = "same_weekday"      # 周环比（同星期对齐）
    MEDIAN_4W = "median_4w"            # 近 4 周同星期中位数
    HOLIDAY_SHIFT = "holiday_shift"    # 节假日位移对齐


BASELINE_LABELS: dict[str, str] = {
    BaselineKind.PREV_DAY.value: "环比（上一日）",
    BaselineKind.SAME_WEEKDAY.value: "周环比（同星期）",
    BaselineKind.MEDIAN_4W.value: "近 4 周中位数",
    BaselineKind.HOLIDAY_SHIFT.value: "节假日位移",
}


class AnomalyLevel(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


ANOMALY_LABELS: dict[str, str] = {
    AnomalyLevel.NORMAL.value: "正常",
    AnomalyLevel.WARNING.value: "异常·关注",
    AnomalyLevel.CRITICAL.value: "异常·重大",
}

ANOMALY_ORDER: dict[str, int] = {
    AnomalyLevel.CRITICAL.value: 0,
    AnomalyLevel.WARNING.value: 1,
    AnomalyLevel.NORMAL.value: 2,
}


class FactorKind(StrEnum):
    DIMENSION = "dimension"    # 单维成员
    COMBO = "combo"            # 多维组合
    COMPONENT = "component"    # 量 / 价（乘法指标内部拆解）


FACTOR_KIND_LABELS: dict[str, str] = {
    FactorKind.DIMENSION.value: "单维因子",
    FactorKind.COMBO.value: "组合因子",
    FactorKind.COMPONENT.value: "量价拆解",
}


class RunStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"        # 组合扫描截断，残差较大
    FAILED = "failed"
    SIMULATED = "simulated"


RUN_STATUS_LABELS: dict[str, str] = {
    RunStatus.SUCCESS.value: "完成",
    RunStatus.PARTIAL.value: "部分解释",
    RunStatus.FAILED.value: "失败",
    RunStatus.SIMULATED.value: "推演",
}


class ReportStatus(StrEnum):
    DRAFT = "draft"
    DELIVERING = "delivering"    # 已发起分发，但仍有渠道未送达（不发布）
    PUBLISHED = "published"


REPORT_STATUS_LABELS: dict[str, str] = {
    ReportStatus.DRAFT.value: "草稿",
    ReportStatus.DELIVERING.value: "投递中",
    ReportStatus.PUBLISHED.value: "已发布",
}


class DeliveryChannel(StrEnum):
    FEISHU = "feishu"
    EMAIL = "email"
    WECOM = "wecom"


DELIVERY_LABELS: dict[str, str] = {
    DeliveryChannel.FEISHU.value: "飞书群",
    DeliveryChannel.EMAIL.value: "邮件",
    DeliveryChannel.WECOM.value: "企微群",
}


class DeliveryStatus(StrEnum):
    """单路投递任务状态：等待 → 已送达 / 失败（失败可单独重试）。"""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


DELIVERY_STATUS_LABELS: dict[str, str] = {
    DeliveryStatus.PENDING.value: "等待中",
    DeliveryStatus.SENT.value: "已送达",
    DeliveryStatus.FAILED.value: "失败",
}

DIMENSION_LABELS: dict[str, str] = {
    "city": "城市",
    "category": "品类",
    "channel": "渠道",
    "store": "门店",
    "segment": "客群",
}

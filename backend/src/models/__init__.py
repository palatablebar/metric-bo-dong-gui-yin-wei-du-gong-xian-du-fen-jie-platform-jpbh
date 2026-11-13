"""ORM 模型聚合导出（Base 用于 create_all）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from src.models.user import User  # noqa: E402
from src.models.metric_def import MetricDef  # noqa: E402
from src.models.dim_tree import DimTree  # noqa: E402
from src.models.fact_daily import FactDaily  # noqa: E402
from src.models.attribution_run import AttributionRun  # noqa: E402
from src.models.swing_factor import SwingFactor  # noqa: E402
from src.models.report_issue import ReportIssue  # noqa: E402
from src.models.report_delivery import ReportDelivery  # noqa: E402
from src.models.audit import AuditLog  # noqa: E402

__all__ = [
    "Base", "User", "MetricDef", "DimTree", "FactDaily",
    "AttributionRun", "SwingFactor", "ReportIssue", "ReportDelivery", "AuditLog",
]

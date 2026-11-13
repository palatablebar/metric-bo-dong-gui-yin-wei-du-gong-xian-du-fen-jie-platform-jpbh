"""角色 -> 权限点。前端副本：frontend/src/constants/roles.ts"""
from __future__ import annotations

from src.constants.enums import Role

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "分析负责人",
    Role.ANALYST.value: "分析师",
    Role.EXEC.value: "管理层（只读）",
}

PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        "metric:read", "metric:write", "dimension:read", "baseline:read",
        "attribution:run", "drilldown:read", "report:read", "report:write",
        "report:distribute", "export:read", "audit:read",
    },
    Role.ANALYST.value: {
        "metric:read", "dimension:read", "baseline:read", "attribution:run",
        "drilldown:read", "report:read", "report:write", "export:read",
    },
    Role.EXEC.value: {"metric:read", "report:read"},
}

METRIC_WRITE_ROLES = (Role.ADMIN.value,)
ATTRIBUTION_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
REPORT_WRITE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
DISTRIBUTE_ROLES = (Role.ADMIN.value,)
EXPORT_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
AUDIT_ROLES = (Role.ADMIN.value,)
READ_ROLES = (Role.ADMIN.value, Role.ANALYST.value, Role.EXEC.value)


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())

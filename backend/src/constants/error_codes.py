"""统一错误码，前端 utils/errorMessage.ts 兜底文案与之对应。"""
from __future__ import annotations

ERROR_CODES: dict[str, str] = {
    "AUTH_INVALID": "邮箱或密码不正确",
    "AUTH_MISSING": "缺少或无效的访问令牌",
    "FORBIDDEN": "当前角色无权执行该操作",
    "NOT_FOUND": "对象不存在",
    "CONFLICT": "对象状态冲突",
    "RATE_LIMITED": "请求过于频繁，请稍后再试",
    "VALIDATION": "请求参数不合法",
    "NO_FACT": "该日期没有事实数据",
    "METRIC_NOT_DECOMPOSABLE": "该指标口径不支持按维度分解",
    "NO_BASELINE": "找不到可用的基线日期（数据天数不足）",
    "RUN_INCOMPLETE": "归因批次未完成，无法生成日报",
    "REPORT_EXISTS": "该批次已生成过日报",
    "INTERNAL": "服务内部错误",
}

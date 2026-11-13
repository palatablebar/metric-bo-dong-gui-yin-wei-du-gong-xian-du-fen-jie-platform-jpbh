"""审计动作中文标签。"""
from __future__ import annotations

ACTIONS: dict[str, str] = {
    "auth.login": "登录",
    "http.mutation": "写请求",
    "metric.update": "修改指标口径",
    "attribution.run": "运行归因",
    "report.create": "生成日报",
    "report.distribute": "分发日报",
    "report.delivery_retry": "重试单路投递",
    "report.update": "修改日报结论",
    "export.report": "导出日报",
}

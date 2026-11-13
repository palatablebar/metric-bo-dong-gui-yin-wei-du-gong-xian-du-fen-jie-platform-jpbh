const FALLBACK: Record<string, string> = {
  AUTH_INVALID: '邮箱或密码不正确',
  AUTH_MISSING: '登录已过期，请重新登录',
  FORBIDDEN: '当前角色无权执行该操作（服务端返回 403）',
  NOT_FOUND: '对象不存在',
  CONFLICT: '对象状态冲突',
  RATE_LIMITED: '请求过于频繁，请稍后再试',
  VALIDATION: '请求参数不合法',
  NO_FACT: '该日期没有事实数据',
  METRIC_NOT_DECOMPOSABLE: '该指标口径不支持按维度分解',
  NO_BASELINE: '找不到可用的基线日期（历史数据不足）',
  RUN_INCOMPLETE: '归因批次未完成，无法生成日报',
  REPORT_EXISTS: '该批次已生成过日报',
  INTERNAL: '服务内部错误',
};

export function errorMessage(payload: unknown, fallback = '操作失败'): string {
  if (typeof payload === 'string' && payload) return payload;
  if (payload && typeof payload === 'object') {
    const data = payload as { code?: string; message?: string; detail?: unknown };
    if (data.code && FALLBACK[data.code]) {
      const extra = typeof data.detail === 'string' ? data.detail : '';
      return extra ? `${FALLBACK[data.code]} · ${extra}` : FALLBACK[data.code];
    }
    if (data.message) return String(data.message);
  }
  return fallback;
}

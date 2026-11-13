export const NAV_ITEMS = [
  { to: '/dashboard', label: '观测台', sub: '指标看板', permission: 'metric:read' },
  { to: '/attribution', label: '归因', sub: '瀑布图', permission: 'attribution:run' },
  { to: '/drilldown', label: '下钻', sub: '树形逐层', permission: 'drilldown:read' },
  { to: '/baseline', label: '基线', sub: '节假日校正', permission: 'baseline:read' },
  { to: '/reports', label: '日报', sub: '生成与分发', permission: 'report:read' },
];

export const TARGET_DATE = '2026-11-09';
export const BASELINE_DATE = '2026-11-02';
export const DEFAULT_TOP_N = 8;

export const ISOBAR_LEGEND = '等压线 = 同波动量级；刻度 = |Δ|/MAD';

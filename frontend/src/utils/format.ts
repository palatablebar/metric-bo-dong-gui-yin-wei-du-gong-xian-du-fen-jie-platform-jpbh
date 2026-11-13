export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return Math.round(value).toLocaleString('zh-CN');
}

export function fmtSigned(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—';
  const rounded = Number(value.toFixed(digits));
  const text = Math.abs(rounded).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return `${rounded > 0 ? '+' : rounded < 0 ? '−' : ''}${text}`;
}

export function fmtPct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '—';
  const rounded = Number(value.toFixed(digits));
  return `${rounded > 0 ? '+' : rounded < 0 ? '−' : ''}${Math.abs(rounded).toFixed(digits)}%`;
}

export function fmtPp(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const rounded = Number(value.toFixed(2));
  return `${rounded > 0 ? '+' : rounded < 0 ? '−' : ''}${Math.abs(rounded).toFixed(2)}pp`;
}

export function fmtRatio(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '—';
  return Number(value.toFixed(digits)).toFixed(digits);
}

export function shortDate(value: string): string {
  return value.slice(5);
}

export function weekdayOf(dateText: string): string {
  const day = new Date(`${dateText}T00:00:00`);
  return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][day.getDay()];
}

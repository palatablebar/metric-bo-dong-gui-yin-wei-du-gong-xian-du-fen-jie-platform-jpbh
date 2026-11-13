/** 共享枚举（前端副本）。后端唯一定义处：backend/src/constants/enums.py */
export type AnomalyLevel = 'normal' | 'warning' | 'critical';

export const ANOMALY_LABELS: Record<AnomalyLevel, string> = {
  normal: '正常',
  warning: '异常·关注',
  critical: '异常·重大',
};

export const ANOMALY_CLASS: Record<AnomalyLevel, string> = {
  normal: 'badge normal',
  warning: 'badge warning',
  critical: 'badge critical',
};

export type BaselineKind = 'prev_day' | 'same_weekday' | 'median_4w' | 'holiday_shift';

export const BASELINE_LABELS: Record<BaselineKind, string> = {
  prev_day: '环比（上一日）',
  same_weekday: '周环比（同星期）',
  median_4w: '近 4 周中位数',
  holiday_shift: '节假日位移',
};

export type MetricKind = 'additive' | 'multiplicative';

export const METRIC_KIND_LABELS: Record<MetricKind, string> = {
  additive: '加法指标',
  multiplicative: '乘法指标',
};

export type FactorKind = 'dimension' | 'combo' | 'component';

export const FACTOR_KIND_LABELS: Record<FactorKind, string> = {
  dimension: '单维因子',
  combo: '组合因子',
  component: '量价拆解',
};

export const DIMENSION_LABELS: Record<string, string> = {
  city: '城市',
  category: '品类',
  channel: '渠道',
  store: '门店',
  segment: '客群',
};

export type ReportStatus = 'draft' | 'delivering' | 'published';

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  draft: '草稿',
  delivering: '投递中',
  published: '已发布',
};

export const DELIVERY_LABELS: Record<string, string> = {
  feishu: '飞书群',
  email: '邮件',
  wecom: '企微群',
};

export type DeliveryStatus = 'pending' | 'sent' | 'failed';

export const DELIVERY_STATUS_LABELS: Record<DeliveryStatus, string> = {
  pending: '等待中',
  sent: '已送达',
  failed: '失败',
};

export const DELIVERY_STATUS_CLASS: Record<DeliveryStatus, string> = {
  pending: 'badge muted',
  sent: 'badge normal',
  failed: 'badge critical',
};

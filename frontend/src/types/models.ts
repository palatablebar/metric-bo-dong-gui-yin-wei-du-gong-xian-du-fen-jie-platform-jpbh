export type Role = 'admin' | 'analyst' | 'exec';

export interface UserInfo {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  role_label: string;
  team: string;
  permissions: string[];
}

export interface Metric {
  id: number;
  code: string;
  name: string;
  unit: string;
  kind: 'additive' | 'multiplicative';
  kind_label: string;
  formula_text: string;
  numerator: string | null;
  denominator: string | null;
  owner: string;
  higher_is_better: boolean;
  description: string;
  decomposable: boolean;
}

export interface TrendPoint {
  date: string;
  weekday: string;
  value: number;
}

export interface TrendPayload {
  metric: Metric;
  series: TrendPoint[];
  latest: TrendPoint;
  previous: TrendPoint | null;
  delta_value: number;
  delta_pct: number;
  peak: number;
  trough: number;
  avg: number;
  days: number;
}

export interface DimensionMember {
  code: string;
  name: string;
  parent_code: string | null;
  level: number;
}

export interface Dimension {
  code: string;
  label: string;
  members: DimensionMember[];
  member_count: number;
}

export interface BaselineCandidate {
  kind: string;
  label: string;
  baseline_date: string | null;
  weekday: string | null;
  base_value: number | null;
  available: boolean;
  note: string;
  delta_value?: number;
  delta_pct?: number;
  z_score?: number;
  points?: { date: string; value: number }[];
  median?: number;
  mad?: number;
  holiday_name?: string | null;
  shift_name?: string | null;
}

export interface BaselinePayload {
  metric: Metric;
  target_date: string;
  target_weekday: string;
  value_now: number;
  candidates: BaselineCandidate[];
  chosen: {
    kind: string;
    label: string;
    baseline_date: string;
    baseline_weekday: string;
    base_value: number;
    delta_value: number;
    delta_pct: number;
  };
  robust: {
    points: number;
    median: number;
    mad: number;
    delta_over_mad: number;
    threshold: number;
    critical_threshold: number;
  };
  z_score: number;
  anomaly_level: 'normal' | 'warning' | 'critical';
  anomaly_label: string;
  is_anomaly: boolean;
  holiday: { is_holiday: boolean; name: string | null; shift_target: string | null; shift_name: string | null };
  reasons: string[];
}

export interface SwingFactor {
  id?: number;
  rank: number;
  kind: string;
  dim_name: string;
  dim_label: string;
  member_code: string;
  member_name: string;
  path: string;
  path_label: string;
  component: string | null;
  value_now: number;
  value_base: number;
  delta_value: number;
  contribution_pp: number;
  contribution_pct: number;
  share_pct: number;
  is_leader?: boolean;
}

export interface RunSummary {
  id: number;
  metric_code: string;
  metric_name: string;
  unit: string;
  target_date: string;
  baseline_kind: string;
  baseline_label: string;
  baseline_date: string;
  status: string;
  status_label: string;
  anomaly_level: string;
  anomaly_label: string;
  z_score: number;
  mad_value: number;
  value_now: number;
  value_base: number;
  delta_value: number;
  delta_pct: number;
  explained_pct: number;
  residual_value: number;
  top_n: number;
  dims: string[];
  triple_total: number;
  conclusion: string;
  created_by: string;
  created_at: string;
}

export interface ComponentEffect {
  id?: number;
  kind?: string;
  dim_name?: string;
  dim_label?: string;
  member_code?: string;
  member_name?: string;
  path?: string;
  path_label?: string;
  value_now: number;
  value_base: number;
  delta_value: number;
  contribution_pp: number;
  contribution_pct: number;
  rank?: number;
}

export interface DimensionBreakdown {
  dim: string;
  dim_label: string;
  members: SwingFactor[];
  explained_value: number;
  residual_value: number;
  explained_pct: number;
}

export interface ExplainedBlock {
  top_n: number;
  explained_value: number;
  explained_pct: number;
  residual_value: number;
  residual_pct: number;
  combos_total: number;
  triples_total: number;
  conservation_ok: boolean;
}

export interface AttributionResult {
  run: RunSummary;
  baseline: BaselinePayload;
  components: ComponentEffect[];
  dimensions: DimensionBreakdown[];
  factors: SwingFactor[];
  factor_pool_size: number;
  explained: ExplainedBlock;
  stored_factors?: number;
}

export interface AttributionDetail {
  run: RunSummary;
  components: ComponentEffect[];
  dimensions: DimensionBreakdown[];
  factors: SwingFactor[];
  factor_pool_size: number;
  explained: ExplainedBlock;
}

export interface DrillChild {
  dim: string;
  dim_label: string;
  member_code: string;
  member_name: string;
  value_now: number;
  value_base: number;
  delta_value: number;
  contribution_pp: number;
  contribution_pct: number;
  share_of_parent: number;
  is_leaf: boolean;
  parent_code?: string | null;
}

export interface DrillPayload {
  run_id: number;
  target_date: string;
  baseline_date: string;
  metric_code: string;
  path: Record<string, string>;
  path_label: string;
  next_dim: string;
  next_dim_label: string;
  chain: string[];
  value_now: number;
  value_base: number;
  delta_value: number;
  delta_pct: number;
  children: DrillChild[];
  child_count: number;
}

export interface Delivery {
  channel: string;
  channel_label: string;
  target: string;
  actor?: string;
  delivered_at?: string;
  status?: string;
}

export interface Report {
  id: number;
  report_date: string;
  title: string;
  metric_code: string;
  run_id: number;
  status: string;
  status_label: string;
  conclusion: string;
  markdown: string;
  deliveries: Delivery[];
  delivery_count: number;
  issued_by: string;
  created_at: string;
  published_at: string | null;
}

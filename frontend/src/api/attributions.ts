import { http } from './client';
import type { AttributionDetail, AttributionResult, BaselinePayload, DrillPayload, RunSummary } from '../types/models';

export const attributionsApi = {
  suggestBaseline: (metricCode: string, targetDate: string) =>
    http.post<BaselinePayload>('/baselines/suggest', { metric_code: metricCode, target_date: targetDate }),
  list: (limit = 20) => http.get<{ items: RunSummary[]; total: number }>(`/attributions?limit=${limit}`),
  run: (metricCode: string, targetDate: string, baselineKind?: string | null, topN = 8) =>
    http.post<AttributionResult>('/attributions', {
      metric_code: metricCode,
      target_date: targetDate,
      baseline_kind: baselineKind || null,
      top_n: topN,
    }),
  detail: (runId: number) => http.get<AttributionDetail>(`/attributions/${runId}`),
  drilldown: (runId: number, path: Record<string, string>) => {
    const query = Object.entries(path)
      .filter(([, value]) => value)
      .map(([key, value]) => `${key}=${encodeURIComponent(value)}`)
      .join('&');
    return http.get<DrillPayload>(`/attributions/${runId}/drilldown${query ? `?${query}` : ''}`);
  },
};

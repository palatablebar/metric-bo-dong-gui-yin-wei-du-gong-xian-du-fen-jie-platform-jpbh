import { http } from './client';
import type { Dimension, Metric, TrendPayload } from '../types/models';

export const metricsApi = {
  list: () => http.get<{ items: Metric[]; total: number }>('/metrics'),
  trend: (code: string, endDate?: string, days = 30) =>
    http.get<TrendPayload>(
      `/metrics/${encodeURIComponent(code)}/trend?days=${days}${endDate ? `&end_date=${endDate}` : ''}`,
    ),
  dimensions: () =>
    http.get<{ items: Dimension[]; total: number; member_total: number }>('/dimensions'),
  patch: (code: string, body: Record<string, unknown>) =>
    http.patch<Metric>(`/metrics/${encodeURIComponent(code)}`, body),
};

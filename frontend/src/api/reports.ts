import { http } from './client';
import type { Report } from '../types/models';

export const reportsApi = {
  list: (limit = 20) => http.get<{ items: Report[]; total: number }>(`/reports?limit=${limit}`),
  create: (runId: number, conclusion = '') =>
    http.post<Report>('/reports', { run_id: runId, conclusion }),
  get: (reportId: number) => http.get<Report>(`/reports/${reportId}`),
  distribute: (reportId: number, targets: { channel: string; target: string }[]) =>
    http.post<Report>(`/reports/${reportId}/distribute`, { targets }),
  retryDelivery: (reportId: number, deliveryId: number) =>
    http.post<Report>(`/reports/${reportId}/deliveries/${deliveryId}/retry`),
  exportMarkdown: async (reportId: number): Promise<string> => {
    const token = localStorage.getItem('swingattr.token');
    const response = await fetch(`/api/exports/report.md?report_id=${reportId}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error(`导出失败（${response.status}）`);
    return response.text();
  },
};

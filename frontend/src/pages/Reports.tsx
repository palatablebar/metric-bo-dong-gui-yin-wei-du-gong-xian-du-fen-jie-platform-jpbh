import { useState } from 'react';
import EmptyState from '../components/common/EmptyState';
import { reportsApi } from '../api/reports';
import { can } from '../constants/roles';
import { DELIVERY_LABELS, DELIVERY_STATUS_CLASS } from '../constants/enums';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../router/guards';
import { uiStore } from '../stores/uiStore';
import { errorMessage } from '../utils/errorMessage';
import type { Report } from '../types/models';

const CHANNELS = [
  { channel: 'feishu', label: '飞书群', target: '经营分析晨会群' },
  { channel: 'email', label: '邮件', target: 'ops-lead@wotian.example' },
  { channel: 'wecom', label: '企微群', target: '生鲜运营值班群' },
];

function download(filename: string, text: string) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

function fmtTime(value: string | null | undefined) {
  return value ? value.replace('T', ' ').slice(0, 16) : '—';
}

export default function Reports() {
  const { user } = useAuth();
  const canDistribute = can(user?.role, 'report:distribute');
  const canExport = can(user?.role, 'export:read');
  const query = useAsync(() => reportsApi.list(20), []);
  const [selected, setSelected] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);

  async function open(report: Report) {
    setSelected(report);
    try {
      const fresh = await reportsApi.get(report.id);
      setSelected(fresh);
    } catch (err) {
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '读取日报失败'), true);
    }
  }

  async function distribute(report: Report) {
    setBusy(true);
    try {
      const targets = CHANNELS.map((item) => ({ channel: item.channel, target: item.target }));
      const updated = await reportsApi.distribute(report.id, targets);
      setSelected(updated);
      const d = updated.dispatch;
      if (d) {
        const parts = [`新送达 ${d.sent} 路`];
        if (d.skipped_sent) parts.push(`跳过已送达 ${d.skipped_sent} 路`);
        if (d.failed) parts.push(`失败 ${d.failed} 路（可单路重试）`);
        uiStore.toast(parts.join(' · '), d.failed > 0);
      }
      query.reload();
    } catch (err) {
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '分发失败'), true);
    } finally {
      setBusy(false);
    }
  }

  async function retry(report: Report, deliveryId: number) {
    setBusy(true);
    try {
      const updated = await reportsApi.retryDelivery(report.id, deliveryId);
      setSelected(updated);
      const task = updated.deliveries.find((item) => item.id === deliveryId);
      if (task?.status === 'sent') {
        uiStore.toast(`${task.channel_label} 已补发送达，累计尝试 ${task.attempts} 次`);
      } else {
        uiStore.toast(`${task?.channel_label ?? '渠道'} 仍未送达：${task?.last_error ?? '未知原因'}`, true);
      }
      query.reload();
    } catch (err) {
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '重试失败'), true);
    } finally {
      setBusy(false);
    }
  }

  async function exportMd(report: Report) {
    try {
      const text = await reportsApi.exportMarkdown(report.id);
      download(`swingattr-report-${report.report_date}-${report.id}.md`, text);
      uiStore.toast('日报 markdown 已导出');
    } catch (err) {
      uiStore.toast(String(err), true);
    }
  }

  const reports = query.data?.items || [];

  return (
    <div className="split">
      <div className="stack">
        <div className="panel">
          <div className="panel-head">
            <h2>日报列表</h2>
            <span className="hint">{reports.length} 份</span>
          </div>
          {!reports.length ? (
            <EmptyState title="还没有日报" hint="先在「归因」页跑一次归因，再点「生成日报」。" />
          ) : (
            <div className="stack" style={{ gap: 8 }}>
              {reports.map((report) => (
                <button
                  key={report.id}
                  className="panel"
                  style={{
                    textAlign: 'left',
                    cursor: 'pointer',
                    padding: '10px 12px',
                    marginTop: 0,
                    boxShadow: 'none',
                    borderColor: selected?.id === report.id ? 'var(--ink)' : undefined,
                  }}
                  onClick={() => open(report)}
                  data-testid={`report-item-${report.id}`}
                >
                  <div className="row" style={{ gap: 6 }}>
                    <span className="num" style={{ fontFamily: 'var(--font-display)' }}>
                      {report.report_date}
                    </span>
                    <span
                      className={`badge ${
                        report.status === 'published' ? 'normal' : report.status === 'delivering' ? 'warning' : 'muted'
                      }`}
                    >
                      {report.status_label}
                    </span>
                    <span className="spacer" />
                    <span className="tiny muted">
                      {report.delivery_summary.total
                        ? `送达 ${report.delivery_summary.sent}/${report.delivery_summary.total}`
                        : '未分发'}
                    </span>
                  </div>
                  <div className="tiny muted" style={{ marginTop: 3 }}>
                    {report.title}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="stack">
        {!selected ? (
          <div className="panel">
            <EmptyState title="选一份日报" hint="左侧点开可看正文、投递任务，并导出 markdown。" />
          </div>
        ) : (
          <>
            <div className="panel" data-testid="report-detail">
              <div className="panel-head">
                <h2>{selected.title}</h2>
                <span className="hint">
                  {selected.status_label} · 由 {selected.issued_by}
                </span>
              </div>
              <div className="row" style={{ marginBottom: 10 }}>
                <button className="btn btn-sm" onClick={() => exportMd(selected)} disabled={!canExport}>
                  导出 markdown
                </button>
                <span className="spacer" />
                {canDistribute ? (
                  <button className="btn btn-sm" disabled={busy} onClick={() => distribute(selected)}>
                    一键分发（飞书 + 邮件 + 企微）
                  </button>
                ) : (
                  <span className="tiny muted">分发需要分析负责人权限</span>
                )}
              </div>
              {canDistribute ? (
                <div className="tiny muted" style={{ marginBottom: 10 }}>
                  已送达的渠道自动跳过、不重复发送；失败的渠道可在下方单路重试。全部送达后日报才发布。
                </div>
              ) : null}
              <div className="panel" style={{ marginTop: 0, padding: '10px 12px', boxShadow: 'none' }}>
                <div className="eyebrow" style={{ marginBottom: 6 }}>
                  投递任务 {selected.delivery_summary.total} 条 · 送达 {selected.delivery_summary.sent} · 失败{' '}
                  {selected.delivery_summary.failed} · 等待 {selected.delivery_summary.pending}
                </div>
                {selected.deliveries.length ? (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>渠道</th>
                        <th>目标</th>
                        <th>状态</th>
                        <th>尝试</th>
                        <th>失败原因</th>
                        <th>送达时间</th>
                        {canDistribute ? <th>操作</th> : null}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.deliveries.map((item) => (
                        <tr key={item.id} data-testid={`delivery-${item.id}`}>
                          <td>{DELIVERY_LABELS[item.channel] || item.channel_label}</td>
                          <td className="tiny">{item.target}</td>
                          <td>
                            <span className={DELIVERY_STATUS_CLASS[item.status]}>{item.status_label}</span>
                          </td>
                          <td className="tiny num">{item.attempts}</td>
                          <td className="tiny" style={{ color: item.last_error ? 'var(--alert)' : undefined }}>
                            {item.last_error || '—'}
                          </td>
                          <td className="tiny num">{fmtTime(item.delivered_at)}</td>
                          {canDistribute ? (
                            <td>
                              {item.status !== 'sent' ? (
                                <button
                                  className="btn btn-sm"
                                  disabled={busy}
                                  onClick={() => retry(selected, item.id)}
                                  data-testid={`retry-delivery-${item.id}`}
                                >
                                  重试
                                </button>
                              ) : (
                                <span className="tiny muted">已送达</span>
                              )}
                            </td>
                          ) : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="tiny muted">还没有投递任务，点「一键分发」创建。</div>
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>日报正文（markdown）</h2>
                <span className="hint">run #{selected.run_id}</span>
              </div>
              <pre
                className="tiny"
                style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  fontFamily: "'Barlow Condensed', monospace",
                  fontSize: '0.78rem',
                  lineHeight: 1.6,
                  maxHeight: 460,
                  overflow: 'auto',
                  background: 'var(--paper)',
                  border: '1px solid var(--rule)',
                  padding: '10px 12px',
                }}
              >
                {selected.markdown}
              </pre>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>结论</h2>
              </div>
              <p style={{ margin: 0, fontSize: '0.86rem' }}>{selected.conclusion}</p>
              <div className="row tiny muted" style={{ marginTop: 8 }}>
                <span>生成于 {fmtTime(selected.created_at)}</span>
                {selected.published_at ? <span>全部送达 · 发布于 {fmtTime(selected.published_at)}</span> : null}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

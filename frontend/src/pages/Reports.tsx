import { useState } from 'react';
import EmptyState from '../components/common/EmptyState';
import LevelBadge from '../components/common/LevelBadge';
import { reportsApi } from '../api/reports';
import { can } from '../constants/roles';
import { DELIVERY_LABELS } from '../constants/enums';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../router/guards';
import { uiStore } from '../stores/uiStore';
import { errorMessage } from '../utils/errorMessage';
import { fmtPct } from '../utils/format';
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

  async function distribute(report: Report, channels: string[]) {
    setBusy(true);
    try {
      const targets = CHANNELS.filter((item) => channels.includes(item.channel)).map((item) => ({
        channel: item.channel,
        target: item.target,
      }));
      const updated = await reportsApi.distribute(report.id, targets);
      setSelected(updated);
      uiStore.toast(`已分发 ${targets.length} 个渠道，累计 ${updated.delivery_count} 条记录`);
      query.reload();
    } catch (err) {
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '分发失败'), true);
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
                    <span className={`badge ${report.status === 'published' ? 'normal' : 'muted'}`}>
                      {report.status_label}
                    </span>
                    <span className="spacer" />
                    <span className="tiny muted">{report.delivery_count} 条分发</span>
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
            <EmptyState title="选一份日报" hint="左侧点开可看正文、分发记录，并导出 markdown。" />
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
                  <>
                    <button className="btn btn-sm" disabled={busy} onClick={() => distribute(selected, ['feishu', 'email'])}>
                      分发到飞书 + 邮件（2 条）
                    </button>
                    <button className="btn btn-sm" disabled={busy} onClick={() => distribute(selected, ['wecom'])}>
                      追加企微
                    </button>
                  </>
                ) : (
                  <span className="tiny muted">分发需要分析负责人权限</span>
                )}
              </div>
              <div className="panel" style={{ marginTop: 0, padding: '10px 12px', boxShadow: 'none' }}>
                <div className="eyebrow" style={{ marginBottom: 6 }}>分发记录 {selected.delivery_count} 条</div>
                {selected.deliveries.length ? (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>渠道</th>
                        <th>目标</th>
                        <th>时间</th>
                        <th>状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.deliveries.map((item, index) => (
                        <tr key={`${item.channel}-${index}`}>
                          <td>{DELIVERY_LABELS[item.channel] || item.channel_label}</td>
                          <td className="tiny">{item.target}</td>
                          <td className="tiny num">{item.delivered_at?.replace('T', ' ').slice(0, 16)}</td>
                          <td>
                            <span className="badge normal">已发送</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="tiny muted">还没有分发记录</div>
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
                <span>生成于 {selected.created_at?.replace('T', ' ').slice(0, 16)}</span>
                {selected.published_at ? <span>发布于 {selected.published_at.replace('T', ' ').slice(0, 16)}</span> : null}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

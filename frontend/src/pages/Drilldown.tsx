import { useState } from 'react';
import EmptyState from '../components/common/EmptyState';
import { attributionsApi } from '../api/attributions';
import { useAsync } from '../hooks/useAsync';
import { errorMessage } from '../utils/errorMessage';
import { fmtInt, fmtPct, fmtPp, fmtSigned } from '../utils/format';
import type { DrillPayload } from '../types/models';

const CHAIN = ['city', 'category', 'channel', 'store', 'segment'];
const CHAIN_LABELS: Record<string, string> = {
  city: '城市',
  category: '品类',
  channel: '渠道',
  store: '门店',
  segment: '客群',
};

export default function Drilldown() {
  const runsQuery = useAsync(() => attributionsApi.list(20), []);
  const [runId, setRunId] = useState<number | null>(null);
  const [path, setPath] = useState<Record<string, string>>({});

  const activeRunId = runId ?? runsQuery.data?.items?.[0]?.id ?? null;
  const drillQuery = useAsync(
    () => (activeRunId ? attributionsApi.drilldown(activeRunId, path) : Promise.resolve(null)),
    [activeRunId, JSON.stringify(path)],
  );
  const drill: DrillPayload | null = drillQuery.data;

  const runs = runsQuery.data?.items || [];

  function pick(city: Record<string, string>) {
    setPath(city);
  }

  function drillInto(member: string) {
    if (!drill) return;
    setPath({ ...path, [drill.next_dim]: member });
  }

  const trails: { dim: string; member: string }[] = CHAIN.filter((dim) => path[dim]).map((dim) => ({
    dim,
    member: path[dim],
  }));

  return (
    <div className="grid-2">
      <div className="stack">
        <div className="panel">
          <div className="panel-head">
            <h2>下钻路径</h2>
            <span className="hint">城市 → 品类 → 渠道 → 门店 → 客群</span>
          </div>
          <div className="row" style={{ marginBottom: 10 }}>
            <select
              className="input"
              style={{ width: 220 }}
              value={activeRunId ?? ''}
              onChange={(event) => {
                setRunId(Number(event.target.value));
                setPath({});
              }}
              data-testid="drill-run-select"
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  #{run.id} · {run.target_date} · {run.metric_name} {fmtPct(run.delta_pct)}
                </option>
              ))}
            </select>
            <button className="btn btn-sm" onClick={() => setPath({})} disabled={!Object.keys(path).length}>
              回到全部
            </button>
          </div>

          <div className="row" style={{ gap: 4 }}>
            <button className={`badge ${Object.keys(path).length ? 'muted' : 'cold'}`} onClick={() => setPath({})} style={{ cursor: 'pointer' }}>
              全部
            </button>
            {trails.map((trail, index) => (
              <span key={trail.dim} className="row" style={{ gap: 4 }}>
                <span className="tiny muted">›</span>
                <button
                  className={`badge ${index === trails.length - 1 ? 'cold' : 'muted'}`}
                  style={{ cursor: 'pointer', textTransform: 'none' }}
                  onClick={() => {
                    const next = { ...path };
                    CHAIN.slice(CHAIN.indexOf(trail.dim) + 1).forEach((dim) => delete next[dim]);
                    setPath(next);
                  }}
                >
                  {CHAIN_LABELS[trail.dim]}: {drill?.path_label?.split(' / ')[index] || trail.member}
                </button>
              </span>
            ))}
          </div>
        </div>

        {drillQuery.error ? (
          <div className="panel">
            <div className="error-banner">
              {errorMessage((drillQuery.error as { payload?: unknown }).payload)}
              <button className="btn btn-sm" style={{ marginLeft: 10 }} onClick={drillQuery.reload}>
                重试
              </button>
            </div>
          </div>
        ) : null}

        {drill ? (
          <div className="panel" data-testid="drill-panel">
            <div className="panel-head">
              <h2>
                下一层 · {drill.next_dim_label || '已到叶子'}
              </h2>
              <span className="hint">
                {drill.path_label} · Δ {fmtSigned(drill.delta_value)}（{fmtPct(drill.delta_pct)}）
              </span>
            </div>
            {drill.child_count ? (
              <div className="scroll-x">
                <table className="table" data-testid="drill-table">
                  <thead>
                    <tr>
                      <th>{drill.next_dim_label}</th>
                      <th className="r">本期</th>
                      <th className="r">基线</th>
                      <th className="r">Δ</th>
                      <th className="r">贡献</th>
                      <th className="r">占父级</th>
                      <th>占比条</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drill.children.map((child) => (
                      <tr
                        key={child.member_code}
                        style={{ cursor: child.is_leaf ? 'default' : 'pointer' }}
                        onClick={() => (child.is_leaf ? undefined : drillInto(child.member_code))}
                      >
                        <td>
                          <b style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.03em' }}>{child.member_name}</b>
                          {child.is_leaf ? <span className="tiny muted"> · 叶子</span> : null}
                        </td>
                        <td className="r">{fmtInt(child.value_now)}</td>
                        <td className="r">{fmtInt(child.value_base)}</td>
                        <td className={`r ${child.delta_value < 0 ? 'neg' : 'pos'}`}>{fmtSigned(child.delta_value)}</td>
                        <td className={`r ${child.contribution_pp < 0 ? 'neg' : 'pos'}`}>{fmtPp(child.contribution_pp)}</td>
                        <td className="r">{child.share_of_parent.toFixed(1)}%</td>
                        <td style={{ minWidth: 120 }}>
                          <div style={{ height: 8, background: 'var(--paper-3)' }}>
                            <div
                              style={{
                                width: `${Math.min(100, Math.abs(child.share_of_parent))}%`,
                                height: '100%',
                                background: child.delta_value < 0 ? 'var(--alert)' : 'var(--good)',
                              }}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="这一层没有成员" hint="换一个归因批次，或回到上一层。" />
            )}
          </div>
        ) : (
          <div className="panel">
            <EmptyState title="选择归因批次" hint="下钻基于已落库的归因批次复算，保证与瀑布图同一口径。" />
          </div>
        )}
      </div>

      <div className="stack">
        <div className="panel">
          <div className="panel-head">
            <h2>为什么能穷举</h2>
          </div>
          <p className="tiny muted" style={{ margin: 0 }}>
            5 个维度的全组合是 3×4×3×8×2 = 576 个，人工不可能逐个比。
            本台的下钻是「逐层收窄」：每一层只比当前父级下的子成员，
            所以城市层最多比 3 个、品类层 4 个…… 一层最多看 8 个数字，
            五层就能定位到具体的门店 × 客群。
          </p>
        </div>
        <div className="panel">
          <div className="panel-head">
            <h2>当前层级</h2>
          </div>
          <dl className="kv">
            <dt>路径</dt>
            <dd>{drill?.path_label ?? '全部'}</dd>
            <dt>指标</dt>
            <dd>{drill?.metric_code ?? '—'}</dd>
            <dt>本期/基线</dt>
            <dd>
              {drill ? `${drill.target_date} / ${drill.baseline_date}` : '—'}
            </dd>
            <dt>父级 Δ</dt>
            <dd>{drill ? `${fmtSigned(drill.delta_value)}（${fmtPct(drill.delta_pct)}）` : '—'}</dd>
            <dt>子成员</dt>
            <dd>{drill?.child_count ?? 0} 个</dd>
          </dl>
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';
import TrendChart from '../components/common/TrendChart';
import LevelBadge from '../components/common/LevelBadge';
import EmptyState from '../components/common/EmptyState';
import ObsCard from '../components/common/ObsCard';
import { attributionsApi } from '../api/attributions';
import { metricsApi } from '../api/metrics';
import { useAsync } from '../hooks/useAsync';
import { useUi, uiStore } from '../stores/uiStore';
import { fmtInt, fmtPct, fmtSigned } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';
import type { Metric, TrendPayload } from '../types/models';

export default function Dashboard() {
  const { metric } = useUi();
  const [metricCode, setMetricCode] = useState(metric);

  const metricsQuery = useAsync(() => metricsApi.list(), []);
  const metrics: Metric[] = metricsQuery.data?.items || [];
  const active = metrics.find((item) => item.code === metricCode) || metrics[0];

  const trendQuery = useAsync(
    () => (active ? metricsApi.trend(active.code, undefined, 30) : Promise.resolve(null)),
    [active?.code],
  );
  const trend: TrendPayload | null = trendQuery.data;
  const runsQuery = useAsync(() => attributionsApi.list(6), []);

  if (trendQuery.error) {
    return (
      <div className="panel">
        <div className="error-banner">
          趋势加载失败：{errorMessage((trendQuery.error as { payload?: unknown }).payload)}
          <button className="btn btn-sm" style={{ marginLeft: 10 }} onClick={trendQuery.reload}>
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="row" style={{ marginBottom: 12 }}>
        {metrics.map((item) => (
          <button
            key={item.code}
            className={`btn btn-sm${item.code === active?.code ? ' btn-primary' : ''}`}
            onClick={() => {
              setMetricCode(item.code);
              uiStore.setMetric(item.code);
            }}
            data-testid={`metric-tab-${item.code}`}
          >
            {item.name}
            <span className="tiny" style={{ marginLeft: 5, opacity: 0.75 }}>
              {item.kind === 'multiplicative' ? '乘' : '加'}
            </span>
          </button>
        ))}
        <span className="spacer" />
        <span className="tiny muted">{active?.formula_text}</span>
      </div>

      {trend ? (
        <div className="readouts" style={{ marginBottom: 12 }} data-testid="dashboard-readouts">
          <ObsCard label="最新值" value={<span>{fmtInt(trend.latest.value)}<small> {active?.unit}</small></span>} hint={`${trend.latest.date} · ${trend.latest.weekday}`} />
          <ObsCard label="日环比" value={fmtPct(trend.delta_pct)} hint={`Δ ${fmtSigned(trend.delta_value)}`} tone={trend.delta_pct < 0 ? 'alert' : 'default'} />
          <ObsCard label="30 天峰值" value={fmtInt(trend.peak)} hint="等压线高点" />
          <ObsCard label="30 天谷值" value={fmtInt(trend.trough)} hint="等压线低点" />
          <ObsCard label="30 天均值" value={fmtInt(trend.avg)} hint="口径：日粒度求和" tone="cold" />
          <ObsCard label="样本" value={<span>{trend.days}<small> 天</small></span>} hint={active?.kind_label} tone="cold" />
        </div>
      ) : null}

      <div className="grid-2">
        <div className="stack">
          <div className="panel">
            <div className="panel-head">
              <h2>{active?.name} · 30 天趋势</h2>
              <span className="hint">虚线 = 归因基线 2026-11-02 · 红点 = 异常日 2026-11-09</span>
            </div>
            {trend ? (
              <TrendChart
                series={trend.series}
                anomalyDate="2026-11-09"
                baselineDate="2026-11-02"
                anomalyLabel="GMV −8.3% · z=4.1"
              />
            ) : (
              <div className="tiny muted">加载中 …</div>
            )}
          </div>

          <div className="panel">
            <div className="panel-head">
              <h2>最近归因批次</h2>
              <span className="hint">点「归因」页可复跑</span>
            </div>
            {runsQuery.data?.items?.length ? (
              <table className="table" data-testid="recent-runs">
                <thead>
                  <tr>
                    <th>目标日</th>
                    <th>指标</th>
                    <th className="r">波动</th>
                    <th className="r">|Δ|/MAD</th>
                    <th className="r">解释度</th>
                    <th>等级</th>
                  </tr>
                </thead>
                <tbody>
                  {runsQuery.data.items.map((run) => (
                    <tr key={run.id}>
                      <td className="num">{run.target_date}</td>
                      <td>{run.metric_name}</td>
                      <td className={`r ${run.delta_pct < 0 ? 'neg' : 'pos'}`}>{fmtPct(run.delta_pct)}</td>
                      <td className="r">{run.z_score.toFixed(2)}</td>
                      <td className="r">{run.explained_pct.toFixed(1)}%</td>
                      <td>
                        <LevelBadge level={run.anomaly_level} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <EmptyState title="还没有归因批次" hint="去「归因」页跑一次 2026-11-09 的 GMV 波动。" />
            )}
          </div>
        </div>

        <div className="stack">
          <div className="panel">
            <div className="panel-head">
              <h2>五维度成员</h2>
              <span className="hint">下钻树</span>
            </div>
            <Dimensions />
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2>口径</h2>
            </div>
            <p className="tiny muted" style={{ margin: 0 }}>
              {active?.description}
              <br />
              加法指标（{metrics.filter((item) => item.kind === 'additive').map((item) => item.name).join(' / ')}）
              直接按维度成员求和分解；
              乘法指标（GMV = 订单量 × 客单价）走对数分解 Δln。
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function Dimensions() {
  const query = useAsync(() => metricsApi.dimensions(), []);
  if (!query.data) return <div className="tiny muted">加载维度树 …</div>;
  return (
    <div className="stack" style={{ gap: 8 }}>
      {query.data.items.map((dim) => (
        <div key={dim.code}>
          <div className="row" style={{ gap: 6 }}>
            <b style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.06em' }}>{dim.label}</b>
            <span className="tiny muted">{dim.member_count} 成员</span>
          </div>
          <div className="row" style={{ gap: 4, marginTop: 3 }}>
            {dim.members.map((member) => (
              <span key={member.code} className="badge muted" style={{ textTransform: 'none', letterSpacing: 0 }}>
                {member.name}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

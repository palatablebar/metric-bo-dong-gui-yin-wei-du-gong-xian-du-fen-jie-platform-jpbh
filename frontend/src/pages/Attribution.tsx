import { useState } from 'react';
import EmptyState from '../components/common/EmptyState';
import LevelBadge from '../components/common/LevelBadge';
import ObsCard from '../components/common/ObsCard';
import WaterfallChart from '../components/common/WaterfallChart';
import { attributionsApi } from '../api/attributions';
import { reportsApi } from '../api/reports';
import { metricsApi } from '../api/metrics';
import { can } from '../constants/roles';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../router/guards';
import { uiStore } from '../stores/uiStore';
import { errorMessage } from '../utils/errorMessage';
import { fmtInt, fmtPct, fmtPp, fmtSigned } from '../utils/format';
import type { AttributionResult, Metric } from '../types/models';

const BASELINE_OPTIONS = [
  { value: '', label: '自动选基线' },
  { value: 'same_weekday', label: '周环比（同星期）' },
  { value: 'prev_day', label: '环比（上一日）' },
  { value: 'median_4w', label: '近 4 周中位数' },
  { value: 'holiday_shift', label: '节假日位移' },
];

export default function Attribution() {
  const { user } = useAuth();
  const metricsQuery = useAsync(() => metricsApi.list(), []);
  const metrics: Metric[] = metricsQuery.data?.items || [];

  const [metricCode, setMetricCode] = useState('gmv');
  const [targetDate, setTargetDate] = useState('2026-11-09');
  const [baselineKind, setBaselineKind] = useState('');
  const [topN, setTopN] = useState(8);
  const [result, setResult] = useState<AttributionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reportId, setReportId] = useState<number | null>(null);

  async function run() {
    setBusy(true);
    setError('');
    setReportId(null);
    try {
      const data = await attributionsApi.run(metricCode, targetDate, baselineKind || null, topN);
      setResult(data);
      const leader = data.factors[0];
      uiStore.toast(
        `归因完成：${data.run.delta_pct.toFixed(2)}%，头号因子 ${leader ? leader.path_label : '—'}（${leader ? leader.contribution_pp.toFixed(2) : '0'}pp）`,
        data.run.delta_pct < 0,
      );
    } catch (err) {
      setResult(null);
      setError(errorMessage((err as { payload?: unknown }).payload, '归因失败'));
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '归因失败'), true);
    } finally {
      setBusy(false);
    }
  }

  async function createReport() {
    if (!result) return;
    try {
      const report = await reportsApi.create(result.run.id, '');
      setReportId(report.id);
      uiStore.toast(`已生成日报 #${report.id}，去「日报」页分发`);
    } catch (err) {
      uiStore.toast(errorMessage((err as { payload?: unknown }).payload, '生成日报失败'), true);
    }
  }

  const canWriteReport = can(user?.role, 'report:write');

  return (
    <>
      <div className="panel" style={{ marginBottom: 12 }}>
        <div className="panel-head">
          <h2>归因参数</h2>
          <span className="hint">加法指标按成员求和 · 乘法指标走 Δln 量价拆解</span>
        </div>
        <div className="row">
          <label className="row" style={{ gap: 5 }}>
            <span className="tiny muted">指标</span>
            <select className="input" style={{ width: 120 }} value={metricCode} onChange={(event) => setMetricCode(event.target.value)}>
              {metrics.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="row" style={{ gap: 5 }}>
            <span className="tiny muted">目标日</span>
            <input className="input" type="date" style={{ width: 150 }} value={targetDate} onChange={(event) => setTargetDate(event.target.value)} data-testid="target-date" />
          </label>
          <label className="row" style={{ gap: 5 }}>
            <span className="tiny muted">基线</span>
            <select className="input" style={{ width: 150 }} value={baselineKind} onChange={(event) => setBaselineKind(event.target.value)}>
              {BASELINE_OPTIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="row" style={{ gap: 5 }}>
            <span className="tiny muted">Top-N</span>
            <input className="input" type="number" min={3} max={20} style={{ width: 74 }} value={topN} onChange={(event) => setTopN(Number(event.target.value))} />
          </label>
          <button className="btn btn-primary" onClick={run} disabled={busy} data-testid="run-attribution">
            {busy ? '分解中 …' : '跑归因'}
          </button>
          <span className="spacer" />
          <button className="btn btn-sm" onClick={createReport} disabled={!result || !canWriteReport}>
            {reportId ? `已生成日报 #${reportId}` : '生成日报'}
          </button>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {!result ? (
        <div className="panel">
          <EmptyState
            title="还没有归因结果"
            hint="选 2026-11-09 的 GMV、基线留空（算法会自己选周环比），点「跑归因」。"
          />
        </div>
      ) : (
        <>
          <div className="readouts" style={{ marginBottom: 12 }} data-testid="attribution-readouts">
            <ObsCard label="本期" value={fmtInt(result.run.value_now)} hint={result.run.target_date} />
            <ObsCard label="基线" value={fmtInt(result.run.value_base)} hint={`${result.run.baseline_date} · ${result.run.baseline_label}`} tone="cold" />
            <ObsCard label="波动" value={fmtPct(result.run.delta_pct)} hint={`Δ ${fmtSigned(result.run.delta_value)}`} tone={result.run.delta_pct < 0 ? 'alert' : 'default'} />
            <ObsCard label="|Δ|/MAD" value={result.run.z_score.toFixed(2)} hint={`MAD ${fmtInt(result.run.mad_value)}`} tone={result.run.anomaly_level === 'normal' ? 'default' : 'alert'} />
            <ObsCard label="解释度" value={`${result.run.explained_pct.toFixed(1)}%`} hint={`残差 ${fmtSigned(result.explained.residual_value)}`} tone="cold" />
            <ObsCard label="扫描组合" value={`${result.explained.triples_total}`} hint="3 维 = 完整划分（全 5 维 576 组）" tone="cold" />
          </div>

          <div className="grid-2">
            <div className="stack">
              <div className="panel">
                <div className="panel-head">
                  <h2>瀑布图 · 波动拆到因子</h2>
                  <span className="hint">
                    <LevelBadge level={result.run.anomaly_level} /> {result.run.baseline_label} · 残差已单列
                  </span>
                </div>
                <WaterfallChart
                  factors={result.factors}
                  deltaTotal={result.run.delta_value}
                  residual={result.explained.residual_value}
                  unit={result.run.unit}
                />
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h2>贡献因子 Top {result.factors.length}</h2>
                  <span className="hint">按 |Δ| 排名 · 组合 = 城市×品类×渠道</span>
                </div>
                <div className="scroll-x">
                  <table className="table" data-testid="factor-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>维度</th>
                        <th>成员</th>
                        <th className="r">本期</th>
                        <th className="r">基线</th>
                        <th className="r">Δ</th>
                        <th className="r">贡献</th>
                        <th className="r">占总波动</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.factors.map((factor) => (
                        <tr key={`${factor.rank}-${factor.member_code}`} className={factor.rank === 1 ? 'lead' : ''}>
                          <td className="r">{factor.rank}</td>
                          <td className="tiny">{factor.dim_label}</td>
                          <td>{factor.path_label}</td>
                          <td className="r">{fmtInt(factor.value_now)}</td>
                          <td className="r">{fmtInt(factor.value_base)}</td>
                          <td className={`r ${factor.delta_value < 0 ? 'neg' : 'pos'}`}>{fmtSigned(factor.delta_value)}</td>
                          <td className={`r ${factor.contribution_pp < 0 ? 'neg' : 'pos'}`}>{fmtPp(factor.contribution_pp)}</td>
                          <td className="r">{factor.contribution_pct.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="row tiny muted" style={{ marginTop: 8 }}>
                  <span>
                    解释度合计 {result.explained.explained_pct.toFixed(2)}% · 残差{' '}
                    {fmtSigned(result.explained.residual_value)}（{result.explained.residual_pct.toFixed(2)}%）
                  </span>
                  <span className="spacer" />
                  <span>{result.explained.conservation_ok ? '守恒校验通过' : '守恒校验异常'}</span>
                </div>
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h2>单维贡献（完整划分 · 残差 0）</h2>
                  <span className="hint">每个维度单独把 Δ 分完</span>
                </div>
                <div className="scroll-x">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>维度</th>
                        <th>成员</th>
                        <th className="r">Δ</th>
                        <th className="r">贡献</th>
                        <th className="r">占该维 Δ</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.dimensions.flatMap((group) =>
                        group.members.slice(0, 3).map((member, index) => (
                          <tr key={`${group.dim}-${member.member_code}`}>
                            <td className="tiny">{index === 0 ? group.dim_label : ''}</td>
                            <td>{member.member_name}</td>
                            <td className={`r ${member.delta_value < 0 ? 'neg' : 'pos'}`}>{fmtSigned(member.delta_value)}</td>
                            <td className="r">{fmtPp(member.contribution_pp)}</td>
                            <td className="r">{member.contribution_pct.toFixed(1)}%</td>
                          </tr>
                        )),
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="stack">
              {result.components.length ? (
                <div className="panel">
                  <div className="panel-head">
                    <h2>量价拆解</h2>
                    <span className="hint">Δln 守恒</span>
                  </div>
                  {result.components.map((item) => (
                    <div key={item.member_code || item.dim_name} style={{ marginBottom: 10 }}>
                      <div className="row">
                        <b style={{ fontFamily: 'var(--font-display)', fontSize: '0.9rem' }}>{item.member_name || item.dim_label}</b>
                        <span className="spacer" />
                        <span className={`num ${item.delta_value < 0 ? 'neg' : 'pos'}`}>{fmtSigned(item.delta_value)}</span>
                      </div>
                      <div className="tiny muted">
                        本期 {fmtInt(item.value_now)} / 基线 {fmtInt(item.value_base)} · 贡献 {fmtPp(item.contribution_pp)} ·
                        Δln {(item as unknown as { delta_ln?: number }).delta_ln?.toFixed(6) ?? '—'}
                      </div>
                      <div style={{ height: 7, background: 'var(--paper-3)', marginTop: 3 }}>
                        <div
                          style={{
                            width: `${Math.min(100, Math.abs(item.contribution_pct))}%`,
                            height: '100%',
                            background: item.delta_value < 0 ? 'var(--alert)' : 'var(--good)',
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="panel">
                <div className="panel-head">
                  <h2>基线选择理由</h2>
                </div>
                <div className="stack" style={{ gap: 6 }}>
                  {result.baseline.reasons.map((reason, index) => (
                    <div key={index} className="tiny" style={{ paddingLeft: 10, borderLeft: '3px solid var(--cold)' }}>
                      {reason}
                    </div>
                  ))}
                </div>
                <dl className="kv" style={{ marginTop: 10 }}>
                  <dt>选中基线</dt>
                  <dd>{result.run.baseline_label} · {result.run.baseline_date}</dd>
                  <dt>稳健中心</dt>
                  <dd>{fmtInt(result.baseline.robust.median)}</dd>
                  <dt>MAD</dt>
                  <dd>{fmtInt(result.baseline.robust.mad)}</dd>
                  <dt>异常等级</dt>
                  <dd>
                    <LevelBadge level={result.run.anomaly_level} label={result.run.anomaly_label} />
                  </dd>
                </dl>
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h2>自动结论</h2>
                </div>
                <p style={{ margin: 0, fontSize: '0.84rem' }}>{result.run.conclusion}</p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

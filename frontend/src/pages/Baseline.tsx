import { useState } from 'react';
import EmptyState from '../components/common/EmptyState';
import LevelBadge from '../components/common/LevelBadge';
import ObsCard from '../components/common/ObsCard';
import { attributionsApi } from '../api/attributions';
import { metricsApi } from '../api/metrics';
import { useAsync } from '../hooks/useAsync';
import { uiStore } from '../stores/uiStore';
import { errorMessage } from '../utils/errorMessage';
import { fmtInt, fmtPct, fmtRatio, fmtSigned } from '../utils/format';
import type { BaselinePayload, Metric } from '../types/models';

export default function Baseline() {
  const metricsQuery = useAsync(() => metricsApi.list(), []);
  const metrics: Metric[] = metricsQuery.data?.items || [];
  const [metricCode, setMetricCode] = useState('gmv');
  const [targetDate, setTargetDate] = useState('2026-11-09');
  const [payload, setPayload] = useState<BaselinePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function suggest() {
    setBusy(true);
    setError('');
    try {
      const data = await attributionsApi.suggestBaseline(metricCode, targetDate);
      setPayload(data);
      uiStore.toast(`基线：${data.chosen.label}（${data.chosen.baseline_date}）；|Δ|/MAD = ${data.z_score.toFixed(2)}`);
    } catch (err) {
      setPayload(null);
      setError(errorMessage((err as { payload?: unknown }).payload, '取基线失败'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="panel" style={{ marginBottom: 12 }}>
        <div className="panel-head">
          <h2>基线设置</h2>
          <span className="hint">同比 / 环比 / 近 4 周移动中位数 + 节假日位移对齐</span>
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
            <input className="input" type="date" style={{ width: 150 }} value={targetDate} onChange={(event) => setTargetDate(event.target.value)} data-testid="baseline-date" />
          </label>
          <button className="btn btn-primary" onClick={suggest} disabled={busy} data-testid="suggest-baseline">
            {busy ? '推算中 …' : '选基线 + 判异常'}
          </button>
          <span className="spacer" />
          <span className="tiny muted">MAD = median(|x − median(x)|)，&gt; 3 判异常</span>
        </div>
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {!payload ? (
        <div className="panel">
          <EmptyState
            title="还没有基线结论"
            hint="试 2026-11-09：目标日是周一，上一日是周日，日环比会被周末效应污染 → 应选周环比。"
          />
        </div>
      ) : (
        <>
          <div className="readouts" style={{ marginBottom: 12 }} data-testid="baseline-readouts">
            <ObsCard label="本期" value={fmtInt(payload.value_now)} hint={`${payload.target_date} · ${payload.target_weekday}`} />
            <ObsCard label="选中基线" value={payload.chosen.label} hint={`${payload.chosen.baseline_date} · ${payload.chosen.baseline_weekday}`} tone="cold" />
            <ObsCard label="波动" value={fmtPct(payload.chosen.delta_pct)} hint={`Δ ${fmtSigned(payload.chosen.delta_value)}`} tone={payload.chosen.delta_pct < 0 ? 'alert' : 'default'} />
            <ObsCard label="MAD" value={fmtInt(payload.robust.mad)} hint={`${payload.robust.points} 个同星期点`} tone="cold" />
            <ObsCard label="|Δ|/MAD" value={fmtRatio(payload.z_score, 3)} hint={`阈值 ${payload.robust.threshold}`} tone={payload.is_anomaly ? 'alert' : 'default'} />
            <ObsCard label="异常等级" value={<LevelBadge level={payload.anomaly_level} />} hint={payload.is_anomaly ? '需要归因' : '正常波动'} />
          </div>

          <div className="grid-2">
            <div className="stack">
              <div className="panel">
                <div className="panel-head">
                  <h2>候选基线</h2>
                  <span className="hint">未选中的也列出来，附不可用原因</span>
                </div>
                <div className="stack" style={{ gap: 8 }}>
                  {payload.candidates.map((candidate) => {
                    const isChosen = candidate.kind === payload.chosen.kind;
                    return (
                      <div
                        key={candidate.kind}
                        className="panel"
                        style={{
                          marginTop: 0,
                          padding: '9px 12px',
                          boxShadow: 'none',
                          borderLeft: `4px solid ${isChosen ? 'var(--cold-deep)' : 'var(--rule-strong)'}`,
                          background: isChosen ? 'oklch(0.52 0.088 245 / 0.05)' : 'var(--card)',
                        }}
                        data-testid={`baseline-candidate-${candidate.kind}`}
                      >
                        <div className="row">
                          <b style={{ fontFamily: 'var(--font-display)', letterSpacing: '0.04em' }}>{candidate.label}</b>
                          {isChosen ? <span className="badge cold">已选中</span> : null}
                          {!candidate.available ? <span className="badge muted">不可用</span> : null}
                          <span className="spacer" />
                          {candidate.available ? (
                            <>
                              <span className="num tiny muted">{candidate.baseline_date}</span>
                              <span className="num">{fmtInt(candidate.base_value)}</span>
                              <span className={`num ${(candidate.delta_pct ?? 0) < 0 ? 'neg' : 'pos'}`}>
                                {fmtPct(candidate.delta_pct ?? 0)}
                              </span>
                            </>
                          ) : null}
                        </div>
                        <div className="tiny muted" style={{ marginTop: 3 }}>
                          {candidate.note}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h2>为什么选它</h2>
                  <span className="hint">结论可回溯，不再凭经验</span>
                </div>
                <div className="stack" style={{ gap: 6 }}>
                  {payload.reasons.map((reason, index) => (
                    <div key={index} className="tiny" style={{ paddingLeft: 10, borderLeft: '3px solid var(--cold)' }}>
                      {reason}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="stack">
              <div className="panel">
                <div className="panel-head">
                  <h2>稳健离散</h2>
                </div>
                {(() => {
                  const medianCandidate = payload.candidates.find((item) => item.kind === 'median_4w');
                  const points = medianCandidate?.points || [];
                  return (
                    <>
                      <table className="table">
                        <thead>
                          <tr>
                            <th>同星期历史点</th>
                            <th className="r">值</th>
                            <th className="r">偏离中位</th>
                          </tr>
                        </thead>
                        <tbody>
                          {points.map((point) => (
                            <tr key={point.date}>
                              <td className="num tiny">{point.date}</td>
                              <td className="r">{fmtInt(point.value)}</td>
                              <td className="r">{fmtSigned(point.value - payload.robust.median)}</td>
                            </tr>
                          ))}
                          <tr>
                            <td className="tiny muted">中位数</td>
                            <td className="r">{fmtInt(payload.robust.median)}</td>
                            <td className="r">{fmtInt(payload.robust.mad)}（MAD）</td>
                          </tr>
                        </tbody>
                      </table>
                      <p className="tiny muted" style={{ marginBottom: 0 }}>
                        用 MAD 而不是标准差：单点尖刺不会把分母抬高，异常更容易被抓出来。
                      </p>
                    </>
                  );
                })()}
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h2>节假日校正</h2>
                </div>
                <dl className="kv">
                  <dt>是否节假日</dt>
                  <dd>{payload.holiday.is_holiday ? payload.holiday.name : '否'}</dd>
                  <dt>位移目标</dt>
                  <dd>{payload.holiday.shift_target ?? '—'}</dd>
                  <dt>对齐节点</dt>
                  <dd>{payload.holiday.shift_name ?? '—'}</dd>
                </dl>
                <p className="tiny muted" style={{ marginBottom: 0 }}>
                  命中节假日时优先做同类节点位移对齐；否则用同星期基线剔除周内节律。
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

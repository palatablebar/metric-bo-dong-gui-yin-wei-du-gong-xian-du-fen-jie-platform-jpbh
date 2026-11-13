import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { authStore } from '../stores/authStore';
import { errorMessage } from '../utils/errorMessage';

const DEMO_ACCOUNTS = [
  { email: 'admin@swingattr.io', who: '林清河', label: '分析负责人' },
  { email: 'analyst@swingattr.io', who: '周到', label: '分析师' },
  { email: 'exec@swingattr.io', who: '苏未', label: '管理层只读' },
];

const READOUTS = [
  { label: 'GMV 环比', value: '−8.30%', hint: '11-09 vs 11-02' },
  { label: '|Δ|/MAD', value: '4.10', hint: '异常阈值 3.0' },
  { label: '头号因子', value: '−5.2pp', hint: '华东×水产×社区团购' },
  { label: '占总降幅', value: '62.7%', hint: 'Top-1 组合' },
];

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('analyst@swingattr.io');
  const [password, setPassword] = useState('Demo@2026');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await authApi.login(email, password);
      authStore.setSession(result.access_token, result.user);
      navigate(result.user.role === 'exec' ? '/reports' : '/dashboard', { replace: true });
    } catch (err) {
      setError(errorMessage((err as { payload?: unknown }).payload, '登录失败'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-left">
        <div className="eyebrow">WOTIAN FRESH · 经营分析组</div>
        <h1>
          每天早会前
          <br />
          先看<em>这只气压计</em>
        </h1>
        <p className="tagline">
          沃田生鲜 8 人分析组。某天 GMV 环比 −8.3%，运营开会 2 小时翻 Excel 找原因；
          这个台把「选基线 → 判异常 → 拆维度 → 出日报」压成一条可复现的链路：
          5 维度 20 个成员、30 天 5,000 条日事实。
        </p>

        <div className="station-cards">
          {READOUTS.map((item) => (
            <div className="station-card" key={item.label}>
              <span>{item.label}</span>
              <b>{item.value}</b>
              <div className="tiny muted">{item.hint}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="login-right">
        <form className="login-card" onSubmit={submit}>
          <div className="eyebrow">值班观测</div>
          <h2>进站 · 观测台登录</h2>
          <p className="sub">指标看板、归因、基线校正、日报分发都在这里。</p>
          <label className="field">
            <span>邮箱</span>
            <input className="input" type="email" value={email} autoComplete="username" onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label className="field">
            <span>密码</span>
            <input className="input" type="password" value={password} autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} required />
          </label>
          <button className="btn btn-primary" style={{ width: '100%' }} type="submit" disabled={busy}>
            {busy ? '校验中 …' : '进站'}
          </button>
          {error ? <div className="form-error">{error}</div> : null}
          <div className="quick-accounts">
            演示账号（密码统一 Demo@2026）：
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => {
                  setEmail(account.email);
                  setPassword('Demo@2026');
                }}
              >
                {account.who} · {account.label}
              </button>
            ))}
          </div>
        </form>
        <div className="tiny muted">
          权限在服务端生效：管理层（exec）调归因 / 基线 / 日报生成 / 分发接口会真实返回 403，不是前端藏按钮。
        </div>
      </section>
    </div>
  );
}

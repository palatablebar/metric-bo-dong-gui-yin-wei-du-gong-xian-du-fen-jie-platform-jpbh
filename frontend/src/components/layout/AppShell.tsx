import { useSyncExternalStore } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { authStore } from '../../stores/authStore';
import { uiStore } from '../../stores/uiStore';
import { NAV_ITEMS } from '../../constants/ui';
import { ROLE_LABELS, can } from '../../constants/roles';
import Toasts from '../common/Toasts';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const state = useSyncExternalStore(authStore.subscribe, authStore.getState);
  const navigate = useNavigate();
  const role = state.user?.role;
  const navItems = NAV_ITEMS.filter((item) => can(role, item.permission));

  function logout() {
    authStore.logout();
    uiStore.toast('已退出观测站');
    navigate('/login', { replace: true });
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-mark">
          swingattr
          <small>OBS</small>
        </div>
        <div className="rail-gauge">
          {Array.from({ length: 14 }).map((_, index) => (
            <span key={index} />
          ))}
        </div>
        <nav className="rail-nav">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="rail-foot">
          沃田生鲜
          <br />
          经营分析组 · 8 人
          <br />
          <span style={{ letterSpacing: '0.06em' }}>{role ? ROLE_LABELS[role] : '未登录'}</span>
        </div>
      </aside>

      <div className="main">
        <div className="station-head">
          <div>
            <div className="sub">WOTIAN FRESH · METRIC OBSERVATORY</div>
            <h1>指标波动归因与维度贡献度分解台</h1>
          </div>
          <div className="station-meta">
            <div>
              <div className="tiny muted">5 维度 20 成员 · 30 天 · 5,000 条日事实</div>
              <div className="who">
                <b>{state.user?.display_name}</b>
                <div className="tiny muted">{state.user?.email}</div>
              </div>
            </div>
            <button className="btn btn-sm" onClick={logout}>
              退出
            </button>
          </div>
        </div>
        {children}
      </div>
      <Toasts />
    </div>
  );
}

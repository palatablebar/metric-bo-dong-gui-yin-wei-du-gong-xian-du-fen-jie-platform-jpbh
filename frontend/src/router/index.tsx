import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import Attribution from '../pages/Attribution';
import Baseline from '../pages/Baseline';
import Dashboard from '../pages/Dashboard';
import Drilldown from '../pages/Drilldown';
import Login from '../pages/Login';
import Reports from '../pages/Reports';
import { RequireAuth, RequirePermission } from './guards';

function Protected({ permission, children }: { permission: string; children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>
        <RequirePermission permission={permission}>{children}</RequirePermission>
      </AppShell>
    </RequireAuth>
  );
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Protected permission="metric:read"><Dashboard /></Protected>} />
      <Route path="/attribution" element={<Protected permission="attribution:run"><Attribution /></Protected>} />
      <Route path="/drilldown" element={<Protected permission="drilldown:read"><Drilldown /></Protected>} />
      <Route path="/baseline" element={<Protected permission="baseline:read"><Baseline /></Protected>} />
      <Route path="/reports" element={<Protected permission="report:read"><Reports /></Protected>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

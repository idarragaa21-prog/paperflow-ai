import { FolderOpen, Clock, Stethoscope } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import ServiceStatusBanner from './ServiceStatusBanner';

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {icon}
        {label}
      </span>
    </NavLink>
  );
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const [hasClinicalSheets, setHasClinicalSheets] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get('/clinical/sheets', { params: { limit: 1 } })
      .then((r) => { if ((r.data as any[]).length > 0) setHasClinicalSheets(true); })
      .catch(() => {});
  }, [user]);

  async function onLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="rc-shell">
      <aside className="rc-sidebar">
        <div className="rc-brand">
          <div>
            <div className="rc-brand-title">PaperFlow AI</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Projects · Library · Extraction</div>
          </div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>alpha</div>
        </div>

        <nav className="rc-nav">
          <NavItem to="/projects" label="Projects" icon={<FolderOpen size={16} />} />
          <NavItem to="/jobs" label="Jobs" icon={<Clock size={16} />} />
          {hasClinicalSheets ? (
            <NavItem to="/clinical" label="Clinical" icon={<Stethoscope size={16} />} />
          ) : null}
        </nav>

        <div style={{ flex: 1 }} />

        <div className="rc-divider" />
        <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 6px 0 6px' }}>
          <div className="rc-muted">{user?.email || ''}</div>
          <button className="rc-btn" onClick={onLogout}>Logout</button>
        </div>

        <div style={{ height: 10 }} />
        <div className="rc-help" style={{ padding: '0 6px 4px 6px' }}>
          local-first research workspace
        </div>
      </aside>

      <main className="rc-main">
        <ServiceStatusBanner />
        <div className="rc-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

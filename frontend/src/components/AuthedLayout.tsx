import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}
    >
      {label}
    </NavLink>
  );
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

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
          <NavItem to="/projects" label="Projects" />
          <NavItem to="/jobs" label="Jobs" />
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
        <div className="rc-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

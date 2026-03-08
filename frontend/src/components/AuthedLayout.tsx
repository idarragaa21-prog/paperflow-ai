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
            <div style={{ fontSize: 12, opacity: 0.74, marginTop: 4 }}>Discover papers, read with evidence, extract data and ship grounded outputs.</div>
          </div>
          <div className="rc-pill rc-pill--soft">RC</div>
        </div>

        <nav className="rc-nav">
          <NavItem to="/projects" label="Research home" />
          <NavItem to="/jobs" label="Operations" />
        </nav>

        <div className="rc-card" style={{ padding: 14 }}>
          <div className="rc-kicker">How the product flows</div>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 8 }}>Research workflow</div>
          <div className="rc-card-list" style={{ gap: 8 }}>
            <div className="rc-help"><strong>1.</strong> Search and save relevant papers.</div>
            <div className="rc-help"><strong>2.</strong> Read PDFs and ask grounded questions.</div>
            <div className="rc-help"><strong>3.</strong> Extract evidence, write and analyze.</div>
          </div>
        </div>

        <div style={{ flex: 1 }} />

        <div className="rc-divider" />
        <div style={{ fontSize: 12, display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 6px 0 6px' }}>
          <div className="rc-user-panel">
            <div className="rc-user-avatar">{(user?.email || 'p').slice(0, 1).toUpperCase()}</div>
            <div>
              <div style={{ fontWeight: 800 }}>{user?.full_name || 'PaperFlow user'}</div>
              <div className="rc-muted">{user?.email || ''}</div>
            </div>
          </div>
          <button className="rc-btn" onClick={onLogout}>Logout</button>
        </div>

        <div style={{ height: 10 }} />
        <div className="rc-help" style={{ padding: '0 6px 4px 6px' }}>
          Internal RC environment
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

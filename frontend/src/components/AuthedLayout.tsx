import { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

function NavItem({ to, label, onClick }: { to: string; label: string; onClick?: () => void }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}
    >
      {label}
    </NavLink>
  );
}

function SidebarContent({ onNav }: { onNav?: () => void }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  async function onLogout() {
    await logout();
    navigate('/login');
    onNav?.();
  }

  return (
    <>
      <div className="rc-brand">
        <div>
          <div className="rc-brand-title">PaperFlow AI</div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Projects · Library · Extraction</div>
        </div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>alpha</div>
      </div>

      <nav className="rc-nav">
        <NavItem to="/projects" label="Projects" onClick={onNav} />
        <NavItem to="/clinical" label="Clinical" onClick={onNav} />
        <NavItem to="/books" label="Books" onClick={onNav} />
        <NavItem to="/jobs" label="Jobs" onClick={onNav} />
        <NavItem to="/settings" label="Settings" onClick={onNav} />
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
    </>
  );
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Cerrar drawer al cambiar de ruta
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);

  async function onLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="rc-shell">
      {/* Desktop sidebar */}
      <aside className="rc-sidebar rc-sidebar--desktop">
        <SidebarContent />
      </aside>

      {/* Mobile topbar */}
      <div className="rc-mobile-topbar">
        <button
          className="rc-hamburger"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <span style={{ fontWeight: 800, letterSpacing: '-0.02em' }}>PaperFlow</span>
        <div className="rc-avatar-btn" onClick={onLogout} title="Logout">
          {(user?.full_name || user?.email || '?')[0].toUpperCase()}
        </div>
      </div>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <>
          <div className="rc-drawer-overlay" onClick={() => setDrawerOpen(false)} />
          <aside className="rc-sidebar rc-sidebar--drawer">
            <SidebarContent onNav={() => setDrawerOpen(false)} />
          </aside>
        </>
      )}

      <main className="rc-main">
        <div className="rc-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

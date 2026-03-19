import { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';

const Icons = {
  Dashboard: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="7" height="7" rx="1.5"/><rect x="11" y="2" width="7" height="5" rx="1.5"/><rect x="2" y="11" width="7" height="7" rx="1.5"/><rect x="11" y="9" width="7" height="9" rx="1.5"/></svg>,
  Projects: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="7" height="7" rx="1.5"/><rect x="11" y="3" width="7" height="7" rx="1.5"/><rect x="2" y="11" width="7" height="7" rx="1.5"/><rect x="11" y="11" width="7" height="7" rx="1.5"/></svg>,
  Clinical: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2v4M8 4h4"/><rect x="3" y="6" width="14" height="12" rx="2"/><path d="M7 10h6M7 13h4"/></svg>,
  Books: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 3h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M8 3v14M12 7h2M12 10h2"/></svg>,
  Jobs: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 2.5"/></svg>,
  Settings: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="3"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/></svg>,
  LogOut: () => <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M13 5l5 5-5 5"/><path d="M18 10H8"/><path d="M8 3H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h4"/></svg>,
};

function NavItem({ to, label, Icon, onClick }: { to: string; label: string; Icon: React.FC; onClick?: () => void }) {
  return (
    <NavLink to={to} onClick={onClick} className={({ isActive }) => `rc-nav-item${isActive ? ' rc-nav-item--active' : ''}`}>
      <Icon />{label}
    </NavLink>
  );
}

function SidebarContent({ onNav }: { onNav?: () => void }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { t } = useI18n();

  async function onLogout() { await logout(); navigate('/login'); onNav?.(); }

  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  return (
    <>
      <div className="rc-brand">
        <div className="rc-brand-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <div>
          <div className="rc-brand-title">PaperFlow</div>
          <div className="rc-brand-sub">{t.nav.brandSub}</div>
        </div>
      </div>

      <nav className="rc-nav">
        <div className="rc-nav-section">{t.nav.overview}</div>
        <NavItem to="/dashboard" label={t.nav.dashboard} Icon={Icons.Dashboard} onClick={onNav} />
        <NavItem to="/projects" label={t.nav.projects} Icon={Icons.Projects} onClick={onNav} />

        <div className="rc-nav-section">{t.nav.tools}</div>
        <NavItem to="/clinical" label={t.nav.clinical} Icon={Icons.Clinical} onClick={onNav} />
        <NavItem to="/books" label={t.nav.books} Icon={Icons.Books} onClick={onNav} />

        <div className="rc-nav-section">{t.nav.system}</div>
        <NavItem to="/jobs" label={t.nav.jobs} Icon={Icons.Jobs} onClick={onNav} />
        <NavItem to="/settings" label={t.nav.settings} Icon={Icons.Settings} onClick={onNav} />
      </nav>

      <div className="rc-sidebar-footer">
        <div className="rc-user-row">
          <div className="rc-avatar">{initials}</div>
          <span className="rc-user-email">{user?.email || ''}</span>
          <button className="rc-logout-btn" onClick={onLogout} title={t.auth.signOut}><Icons.LogOut /></button>
        </div>
        <div style={{ padding:'2px 10px 4px',fontSize:10,color:'rgba(255,255,255,0.2)',letterSpacing:'0.03em' }}>
          {t.nav.localFirst}
        </div>
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
  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);
  async function onLogout() { await logout(); navigate('/login'); }
  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  return (
    <div className="rc-shell">
      <aside className="rc-sidebar rc-sidebar--desktop"><SidebarContent /></aside>

      <div className="rc-mobile-topbar">
        <button className="rc-hamburger" onClick={() => setDrawerOpen(true)} aria-label="Menu">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
        <span className="rc-mobile-topbar-title">PaperFlow</span>
        <button className="rc-avatar-btn" onClick={onLogout} title="Sign out">{initials}</button>
      </div>

      {drawerOpen && (
        <>
          <div className="rc-drawer-overlay" onClick={() => setDrawerOpen(false)} />
          <aside className="rc-sidebar rc-sidebar--drawer"><SidebarContent onNav={() => setDrawerOpen(false)} /></aside>
        </>
      )}

      <main className="rc-main">
        <div className="rc-container"><Outlet /></div>
      </main>
    </div>
  );
}

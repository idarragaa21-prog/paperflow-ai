import { useEffect, useState, type ReactElement } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';
import OnboardingTour, { useOnboarding } from './OnboardingTour';

const Icons = {
  Dashboard: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="7" height="7" rx="1.5"/><rect x="11" y="2" width="7" height="5" rx="1.5"/><rect x="2" y="11" width="7" height="7" rx="1.5"/><rect x="11" y="9" width="7" height="9" rx="1.5"/></svg>,
  Projects: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="7" height="7" rx="1.5"/><rect x="11" y="3" width="7" height="7" rx="1.5"/><rect x="2" y="11" width="7" height="7" rx="1.5"/><rect x="11" y="11" width="7" height="7" rx="1.5"/></svg>,
  Clinical: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2v4M8 4h4"/><rect x="3" y="6" width="14" height="12" rx="2"/><path d="M7 10h6M7 13h4"/></svg>,
  Books: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M4 3h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M8 3v14M12 7h2M12 10h2"/></svg>,
  DeepResearch: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="8" r="5"/><path d="M14 12l3 3"/><path d="M4 17h12"/><path d="M7 8h6"/></svg>,
  Jobs: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l2.5 2.5"/></svg>,
  Settings: () => <svg className="rc-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="10" cy="10" r="3"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/></svg>,
  Logout: () => <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M13 5l5 5-5 5"/><path d="M18 10H8"/><path d="M8 3H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h4"/></svg>,
};

type NavItemProps = {
  to: string;
  label: string;
  icon: () => ReactElement;
  onClick?: () => void;
  end?: boolean;
};

function NavItem({ to, label, icon: Icon, onClick, end = false }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) => `rc-nav-item${isActive ? ' rc-nav-item--active' : ''}`}
    >
      <Icon />
      <span>{label}</span>
    </NavLink>
  );
}

type SidebarContentProps = {
  onNav?: () => void;
  onLogout: () => Promise<void>;
};

function SidebarContent({ onNav, onLogout }: SidebarContentProps) {
  const { t } = useI18n();
  const user = useAuthStore((s) => s.user);
  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  return (
    <>
      <div className="rc-brand">
        <div className="rc-brand-logo">PF</div>
        <div className="rc-brand-copy">
          <div className="rc-brand-title">PaperFlow</div>
          <div className="rc-brand-sub">AI Research Workspace</div>
        </div>
      </div>

      <div className="rc-nav-group">
        <div className="rc-nav-group__label">{t.nav.overview}</div>
        <nav className="rc-nav-list">
          <NavItem to="/dashboard" label={t.nav.dashboard} icon={Icons.Dashboard} onClick={onNav} />
          <NavItem to="/projects" label={t.nav.projects} icon={Icons.Projects} onClick={onNav} />
          <NavItem to="/clinical" label={t.nav.clinical} icon={Icons.Clinical} onClick={onNav} />
        </nav>
      </div>

      <div className="rc-nav-group">
        <div className="rc-nav-group__label">{t.nav.tools}</div>
        <nav className="rc-nav-list">
          <NavItem to="/deep-research" label="Deep Research" icon={Icons.DeepResearch} onClick={onNav} />
          <NavItem to="/knowledge" label="Books & PDF" icon={Icons.Books} onClick={onNav} />
          <NavItem to="/jobs" label={t.nav.jobs} icon={Icons.Jobs} onClick={onNav} />
          <NavItem to="/settings" label={t.nav.settings} icon={Icons.Settings} onClick={onNav} />
        </nav>
      </div>

      <div className="rc-user-card">
        <button className="rc-avatar-btn" onClick={() => void onLogout()} title={t.auth.signOut}>{initials}</button>
        <div className="rc-user-meta">
          <strong>{user?.full_name || 'Research user'}</strong>
          <span className="rc-user-email">{user?.email || ''}</span>
        </div>
        <button className="rc-logout-btn" onClick={() => void onLogout()} title={t.auth.signOut} aria-label={t.auth.signOut}>
          <Icons.Logout />
        </button>
      </div>
      <div className="rc-sidebar-footnote">{t.nav.localFirst}</div>
    </>
  );
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();
  const navigate = useNavigate();
  const { showOnboarding, dismissOnboarding } = useOnboarding();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  async function onLogout() {
    await logout();
    navigate('/login');
    setDrawerOpen(false);
  }

  return (
    <div className="rc-shell" data-testid="app-shell">
      {showOnboarding && <OnboardingTour onDone={dismissOnboarding} />}

      <aside className="rc-sidebar rc-sidebar--desktop">
        <SidebarContent onLogout={onLogout} />
      </aside>

      <div className="rc-mobile-topbar">
        <button className="rc-hamburger" onClick={() => setDrawerOpen(true)} aria-label="Open menu">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <div className="rc-mobile-topbar-brand">
          <span className="rc-mobile-topbar-logo">PF</span>
          <span className="rc-mobile-topbar-title">PaperFlow</span>
        </div>
        <button className="rc-avatar-btn" onClick={() => void onLogout()} title="Sign out">{initials}</button>
      </div>

      {drawerOpen && (
        <>
          <div className="rc-drawer-overlay" onClick={() => setDrawerOpen(false)} />
          <aside className="rc-sidebar rc-sidebar--drawer">
            <SidebarContent onNav={() => setDrawerOpen(false)} onLogout={onLogout} />
          </aside>
        </>
      )}

      <main className="rc-main rc-page-enter">
        <div className="rc-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

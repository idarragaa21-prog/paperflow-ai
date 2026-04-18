import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';
import OnboardingTour, { useOnboarding } from './OnboardingTour';

function Icon({ path, children }: { path?: string; children?: React.ReactNode }) {
  return (
    <svg className="pg-side-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {path ? <path d="" /> : null}
      {children}
    </svg>
  );
}

const IconDashboard = () => (
  <Icon>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </Icon>
);
const IconProjects = () => (
  <Icon>
    <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4l2 2H20a1.5 1.5 0 0 1 1.5 1.5V18A1.5 1.5 0 0 1 20 19.5H4.5A1.5 1.5 0 0 1 3 18Z" />
  </Icon>
);
const IconSearch = () => (
  <Icon>
    <circle cx="11" cy="11" r="7" />
    <line x1="16.5" y1="16.5" x2="21" y2="21" />
  </Icon>
);
const IconClinical = () => (
  <Icon>
    <path d="M12 22s-7-4.35-7-10a7 7 0 0 1 14 0c0 5.65-7 10-7 10Z" />
    <circle cx="12" cy="12" r="2.5" />
  </Icon>
);
const IconAgent = () => (
  <Icon>
    <rect x="4" y="7" width="16" height="12" rx="2" />
    <path d="M9 7V4h6v3M9 13h.01M15 13h.01M9 17h6" />
  </Icon>
);
const IconJobs = () => (
  <Icon>
    <circle cx="12" cy="12" r="9" />
    <polyline points="12 7 12 12 15.5 14" />
  </Icon>
);
const IconSettings = () => (
  <Icon>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
  </Icon>
);
const IconMenu = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
);
const IconLogout = () => (
  <Icon>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </Icon>
);

type SideLink = { to: string; label: string; icon: React.ReactNode };

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { t } = useI18n();
  const [userOpen, setUserOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const userRef = useRef<HTMLDivElement | null>(null);
  const { showOnboarding, dismissOnboarding } = useOnboarding();

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(e.target as Node)) setUserOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  async function onLogout() {
    setUserOpen(false);
    await logout();
    navigate('/login');
  }

  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  const workspace: SideLink[] = [
    { to: '/dashboard', label: t.nav.dashboard, icon: <IconDashboard /> },
    { to: '/projects', label: t.nav.projects, icon: <IconProjects /> },
    { to: '/deep-research', label: t.nav.deepResearch, icon: <IconSearch /> },
    { to: '/clinical', label: t.nav.clinical, icon: <IconClinical /> },
  ];
  const advanced: SideLink[] = [
    { to: '/agent-hub', label: t.nav.agentHub, icon: <IconAgent /> },
    { to: '/jobs', label: t.nav.jobs, icon: <IconJobs /> },
    { to: '/settings', label: t.nav.settings, icon: <IconSettings /> },
  ];

  const sidebarContent = (
    <>
      <Link to="/dashboard" className="pg-brand" onClick={() => setMobileOpen(false)}>
        <span className="pg-brand-mark">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </span>
        PaperFlow
      </Link>

      <div className="pg-side-section">Workspace</div>
      {workspace.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={() => setMobileOpen(false)}
          className={({ isActive }) => `pg-side-link${isActive ? ' active' : ''}`}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}

      <div className="pg-side-section">Avanzado</div>
      {advanced.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          onClick={() => setMobileOpen(false)}
          className={({ isActive }) => `pg-side-link${isActive ? ' active' : ''}`}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}

      <div className="pg-side-footer">
        <div style={{ position: 'relative' }} ref={userRef}>
          <button type="button" className="pg-side-user" onClick={() => setUserOpen((o) => !o)}>
            <span className="pg-side-user-avatar">{initials}</span>
            <span className="pg-side-user-meta">
              <span className="pg-side-user-name">{user?.full_name || 'Investigador'}</span>
              <span className="pg-side-user-email">{user?.email}</span>
            </span>
          </button>
          {userOpen && (
            <div className="pg-avatar-menu pg-fade-in" style={{ position: 'absolute', bottom: 60, left: 0, right: 0, width: 'auto' }}>
              <Link to="/settings" onClick={() => setUserOpen(false)}>{t.nav.settings}</Link>
              <Link to="/dashboard" onClick={() => setUserOpen(false)}>{t.nav.dashboard}</Link>
              <div className="pg-menu-sep" />
              <button type="button" onClick={onLogout} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <IconLogout /> Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="pg-app">
      {showOnboarding && <OnboardingTour onDone={dismissOnboarding} />}

      <aside className={`pg-sidebar${mobileOpen ? ' open' : ''}`}>{sidebarContent}</aside>
      <div
        className={`pg-side-backdrop${mobileOpen ? ' open' : ''}`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      <div className="pg-content">
        <div className="pg-content-bar">
          <button
            type="button"
            className="pg-btn pg-btn--ghost pg-btn--sm pg-menu-toggle"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Menú"
          >
            <IconMenu />
          </button>
          <div className="pg-spacer" />
        </div>
        <main className="pg-content-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

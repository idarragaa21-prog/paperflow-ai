import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { useI18n } from '../i18n';
import OnboardingTour, { useOnboarding } from './OnboardingTour';

function BrandMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function ChevronDown() {
  return (
    <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="5 8 10 13 15 8" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

type PrimaryLink = { to: string; label: string };

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { t } = useI18n();
  const [avatarOpen, setAvatarOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const avatarRef = useRef<HTMLDivElement | null>(null);
  const advancedRef = useRef<HTMLDivElement | null>(null);
  const { showOnboarding, dismissOnboarding } = useOnboarding();

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (avatarRef.current && !avatarRef.current.contains(e.target as Node)) setAvatarOpen(false);
      if (advancedRef.current && !advancedRef.current.contains(e.target as Node)) setAdvancedOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  async function onLogout() {
    setAvatarOpen(false);
    await logout();
    navigate('/login');
  }

  const initials = (user?.full_name || user?.email || '?').slice(0, 2).toUpperCase();

  const primary: PrimaryLink[] = [
    { to: '/dashboard', label: t.nav.dashboard },
    { to: '/projects', label: t.nav.projects },
    { to: '/deep-research', label: t.nav.deepResearch },
  ];

  const advanced: Array<{ to: string; label: string; hint: string }> = [
    { to: '/clinical', label: t.nav.clinical, hint: 'Respuestas clínicas rápidas' },
    { to: '/agent-hub', label: t.nav.agentHub, hint: 'Workflows automatizados' },
    { to: '/jobs', label: t.nav.jobs, hint: 'Cola de trabajos en segundo plano' },
  ];

  return (
    <div className="pg-shell">
      {showOnboarding && <OnboardingTour onDone={dismissOnboarding} />}

      <header className="pg-topbar">
        <div className="pg-topbar-inner">
          <Link to="/dashboard" className="pg-brand">
            <span className="pg-brand-mark"><BrandMark /></span>
            PaperFlow
          </Link>

          <nav className={`pg-nav${mobileOpen ? ' pg-nav--open' : ''}`}>
            {primary.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) => (isActive ? 'active' : '')}
              >
                {item.label}
              </NavLink>
            ))}

            <div className="pg-dropdown" ref={advancedRef}>
              <button type="button" onClick={() => setAdvancedOpen((o) => !o)}>
                Avanzado <ChevronDown />
              </button>
              {advancedOpen && (
                <div className="pg-dropdown-panel pg-fade-in">
                  {advanced.map((item) => (
                    <Link key={item.to} to={item.to} onClick={() => { setAdvancedOpen(false); setMobileOpen(false); }}>
                      {item.label}
                      <small>{item.hint}</small>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </nav>

          <div className="pg-nav-spacer" />

          <div className="pg-topbar-right">
            <Link to="/settings" className="pg-icon-btn pg-hidden-sm" aria-label={t.nav.settings}>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="10" r="3" />
                <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4" />
              </svg>
            </Link>

            <div style={{ position: 'relative' }} ref={avatarRef}>
              <button
                type="button"
                className="pg-avatar"
                onClick={() => setAvatarOpen((o) => !o)}
                aria-label={user?.email || 'Account'}
              >
                {initials}
              </button>
              {avatarOpen && (
                <div className="pg-avatar-menu pg-fade-in">
                  <div style={{ padding: '8px 12px' }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{user?.full_name || 'Investigador'}</div>
                    <div style={{ color: 'var(--pg-soft)', fontSize: 12 }}>{user?.email}</div>
                  </div>
                  <div className="pg-menu-sep" />
                  <Link to="/settings" onClick={() => setAvatarOpen(false)}>{t.nav.settings}</Link>
                  <Link to="/dashboard" onClick={() => setAvatarOpen(false)}>{t.nav.dashboard}</Link>
                  <div className="pg-menu-sep" />
                  <button type="button" onClick={onLogout}>Cerrar sesión</button>
                </div>
              )}
            </div>

            <button
              type="button"
              className="pg-icon-btn pg-menu-toggle"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Menú"
            >
              <MenuIcon />
            </button>
          </div>
        </div>
      </header>

      <main className="pg-main">
        <div className="pg-container">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

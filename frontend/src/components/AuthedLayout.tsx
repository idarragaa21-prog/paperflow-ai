import { NavLink, Outlet, matchPath, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

type IconName =
  | 'home'
  | 'references'
  | 'writer'
  | 'extract'
  | 'search'
  | 'review'
  | 'chat'
  | 'report'
  | 'notes'
  | 'jobs'
  | 'support'
  | 'projects';

type NavItemConfig = {
  label: string;
  to: string;
  icon: IconName;
  exact?: boolean;
};

function NavGlyph({ name }: { name: IconName }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };

  switch (name) {
    case 'references':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M7 6.5h10" />
          <path {...common} d="M7 12h10" />
          <path {...common} d="M7 17.5h7" />
          <path {...common} d="M4.5 6.5h.01" />
          <path {...common} d="M4.5 12h.01" />
          <path {...common} d="M4.5 17.5h.01" />
        </svg>
      );
    case 'writer':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M4 20l4.5-1 9.8-9.8a1.8 1.8 0 0 0-2.5-2.5L6 16.5 5 21z" />
          <path {...common} d="M13.5 7.5l3 3" />
        </svg>
      );
    case 'extract':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect {...common} x="4" y="4" width="16" height="16" rx="2.5" />
          <path {...common} d="M8 9h8" />
          <path {...common} d="M8 13h8" />
          <path {...common} d="M8 17h4" />
        </svg>
      );
    case 'search':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle {...common} cx="11" cy="11" r="6.5" />
          <path {...common} d="M16 16l4 4" />
        </svg>
      );
    case 'review':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M4 8h16" />
          <path {...common} d="M4 12h10" />
          <path {...common} d="M4 16h7" />
          <path {...common} d="M17 15l2 2 3-4" />
        </svg>
      );
    case 'chat':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6A2.5 2.5 0 0 1 16.5 15H10l-4 4v-4.5A2.5 2.5 0 0 1 5 12.5z" />
        </svg>
      );
    case 'report':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M7 4h7l4 4v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
          <path {...common} d="M14 4v4h4" />
          <path {...common} d="M9 13h6" />
          <path {...common} d="M9 17h4" />
        </svg>
      );
    case 'notes':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M6 4h12a2 2 0 0 1 2 2v12H8a2 2 0 0 0-2 2V4z" />
          <path {...common} d="M8 8h8" />
          <path {...common} d="M8 12h8" />
        </svg>
      );
    case 'jobs':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle {...common} cx="12" cy="12" r="8" />
          <path {...common} d="M12 8v5l3 2" />
        </svg>
      );
    case 'support':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle {...common} cx="12" cy="12" r="8.5" />
          <path {...common} d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2 2-2 3.5" />
          <path {...common} d="M12 17h.01" />
        </svg>
      );
    case 'projects':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M4 6.5A2.5 2.5 0 0 1 6.5 4h3A2.5 2.5 0 0 1 12 6.5V9H4z" />
          <path {...common} d="M12 9V6.5A2.5 2.5 0 0 1 14.5 4h3A2.5 2.5 0 0 1 20 6.5V9h-8z" />
          <path {...common} d="M4 12h8v8H6.5A2.5 2.5 0 0 1 4 17.5z" />
          <path {...common} d="M12 12h8v5.5a2.5 2.5 0 0 1-2.5 2.5H12z" />
        </svg>
      );
    case 'home':
    default:
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path {...common} d="M4 10.5L12 4l8 6.5" />
          <path {...common} d="M6.5 9.5V20h11V9.5" />
        </svg>
      );
  }
}

function SidebarNavItem({ to, label, icon, exact }: NavItemConfig) {
  return (
    <NavLink to={to} end={exact} className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}>
      <span className="rc-nav-item__icon">
        <NavGlyph name={icon} />
      </span>
      <span>{label}</span>
    </NavLink>
  );
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();

  const projectMatch = matchPath('/projects/:projectId/*', location.pathname);
  const projectId = projectMatch?.params.projectId;
  const inProject = Boolean(projectId);
  const isDiscoverRoute = location.pathname.endsWith('/research') || location.pathname.endsWith('/search');

  const projectMainNav: NavItemConfig[] = projectId
    ? [
        { label: 'Inicio', to: `/projects/${projectId}/research`, icon: 'home', exact: true },
        { label: 'Referencias', to: `/projects/${projectId}/references`, icon: 'references' },
        { label: 'Escritor', to: `/projects/${projectId}/drafts`, icon: 'writer' },
        { label: 'Extraer datos', to: `/projects/${projectId}/meta`, icon: 'extract' },
        { label: 'Busqueda IA', to: `/projects/${projectId}/search`, icon: 'search', exact: true },
        { label: 'Revision de literatura', to: `/projects/${projectId}/screening`, icon: 'review' },
        { label: 'Chat con PDF', to: `/projects/${projectId}/reader`, icon: 'chat' },
        { label: 'Informe de investigacion', to: `/projects/${projectId}/analysis`, icon: 'report' },
      ]
    : [];

  const projectLibraryNav: NavItemConfig[] = projectId
    ? [
        { label: 'Mis chats', to: `/projects/${projectId}/reader`, icon: 'chat' },
        { label: 'Mis cuadernos', to: `/projects/${projectId}/notes`, icon: 'notes' },
        { label: 'Panel (Antiguo)', to: '/projects', icon: 'projects', exact: true },
        { label: 'Historial (Antiguo)', to: '/jobs', icon: 'jobs', exact: true },
      ]
    : [];

  const generalNav: NavItemConfig[] = [
    { label: 'Inicio de investigacion', to: '/projects', icon: 'projects', exact: true },
    { label: 'Operaciones', to: '/jobs', icon: 'jobs', exact: true },
  ];

  async function onLogout() {
    await logout();
    navigate('/login');
  }

  const userName = user?.full_name || user?.email?.split('@')[0] || 'PaperFlow';

  return (
    <div className={`rc-shell ${inProject ? 'rc-shell--project' : ''}`}>
      <aside className="rc-sidebar">
        <div className="rc-sidebar__top">
          <div className="rc-brand rc-brand--clean">
            <div className="rc-brand-lockup">
              <span className="rc-brand-dot" />
              <div className="rc-brand-title">PaperFlow</div>
            </div>
            <button type="button" className="rc-sidebar-collapse" aria-label="Contraer barra lateral">
              <span />
              <span />
            </button>
          </div>

          {inProject ? (
            <>
              <div className="rc-sidebar-section">
                <div className="rc-sidebar-section__title">Workspace</div>
                <nav className="rc-nav">
                  {projectMainNav.map((item) => (
                    <SidebarNavItem key={item.label} {...item} />
                  ))}
                </nav>
              </div>

              <div className="rc-sidebar-divider" />

              <div className="rc-sidebar-section">
                <div className="rc-sidebar-section__title">Colecciones</div>
                <nav className="rc-nav">
                  {projectLibraryNav.map((item) => (
                    <SidebarNavItem key={item.label} {...item} />
                  ))}
                </nav>
              </div>
            </>
          ) : (
            <>
              <div className="rc-sidebar-section">
                <div className="rc-sidebar-section__title">Operacion</div>
                <nav className="rc-nav">
                  {generalNav.map((item) => (
                    <SidebarNavItem key={item.label} {...item} />
                  ))}
                </nav>
              </div>
              <div className="rc-sidebar-note">
                <div className="rc-sidebar-section__title">Flujo recomendado</div>
                <p>
                  Busca, guarda, lee con evidencia, extrae datos y termina con un reporte reproducible dentro del mismo
                  proyecto.
                </p>
              </div>
            </>
          )}
        </div>

        <div className="rc-sidebar__bottom">
          <a className="rc-sidebar-support" href="mailto:support@paperflow.dev">
            <span className="rc-nav-item__icon">
              <NavGlyph name="support" />
            </span>
            <span>Help &amp; Support</span>
          </a>

          <div className="rc-user-panel rc-user-panel--sidebar">
            <div className="rc-user-avatar">{userName.slice(0, 1).toUpperCase()}</div>
            <div>
              <div className="rc-user-name">{userName}</div>
              <div className="rc-user-email">{user?.email || ''}</div>
            </div>
          </div>

          <button className="rc-btn rc-btn--sidebar" onClick={onLogout}>
            Cerrar sesion
          </button>
        </div>
      </aside>

      <main className={`rc-main ${isDiscoverRoute ? 'rc-main--discover' : ''}`}>
        <div className={`rc-container ${isDiscoverRoute ? 'rc-container--discover' : ''}`}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { Clock, FolderOpen, LogOut, Stethoscope } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import ServiceStatusBanner from './ServiceStatusBanner';

function NavItem({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

function UserAvatar({ email }: { email: string }) {
  const initials = email
    ? email.slice(0, 2).toUpperCase()
    : '?';
  return <div className="rc-user-avatar">{initials}</div>;
}

export default function AuthedLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const params = useParams<{ projectId?: string }>();

  const [hasClinicalSheets, setHasClinicalSheets] = useState(false);
  const [projectName, setProjectName] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api.get('/clinical/sheets', { params: { limit: 1 } })
      .then((r) => { if ((r.data as any[]).length > 0) setHasClinicalSheets(true); })
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!params.projectId) { setProjectName(null); return; }
    api.get(`/projects/${params.projectId}`)
      .then((r) => setProjectName((r.data as any)?.title || null))
      .catch(() => setProjectName(null));
  }, [params.projectId]);

  async function onLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="rc-shell">
      {/* ── Sidebar ── */}
      <aside className="rc-sidebar">
        {/* Brand */}
        <div className="rc-brand">
          <div className="rc-brand-logo">P</div>
          <div className="rc-brand-text">
            <span className="rc-brand-title">PaperFlow</span>
            <span className="rc-brand-sub">AI Research</span>
          </div>
          <span className="rc-tag rc-tag--slate" style={{ fontSize: 10 }}>alpha</span>
        </div>

        {/* Nav */}
        <div className="rc-nav">
          <div className="rc-nav-section-label">Workspace</div>
          <NavItem to="/projects" label="Projects"  icon={<FolderOpen  size={15} />} />
          <NavItem to="/jobs"     label="Jobs"       icon={<Clock       size={15} />} />
          {hasClinicalSheets && (
            <NavItem to="/clinical" label="Clinical" icon={<Stethoscope size={15} />} />
          )}
        </div>

        {/* Project breadcrumb when inside a project */}
        {projectName && (
          <div style={{ padding: '0 8px' }}>
            <div className="rc-nav-section-label">Current project</div>
            <div
              style={{
                padding: '6px 10px',
                borderRadius: 9,
                background: 'rgba(79,70,229,0.05)',
                border: '1px solid var(--rc-primary-border)',
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--rc-primary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                cursor: 'pointer',
              }}
              onClick={() => navigate('/projects')}
            >
              {projectName}
            </div>
          </div>
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* User */}
        <div className="rc-sidebar-bottom">
          <UserAvatar email={user?.email || ''} />
          <div className="rc-user-info">
            <span className="rc-user-email">{user?.email || ''}</span>
          </div>
          <button
            className="rc-btn rc-btn--ghost"
            style={{ padding: '6px', borderRadius: 8 }}
            title="Logout"
            onClick={onLogout}
          >
            <LogOut size={14} style={{ color: 'var(--rc-muted)' }} />
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="rc-main">
        {/* Topbar */}
        <div className="rc-topbar">
          <div className="rc-topbar-breadcrumb">
            <span
              style={{ cursor: 'pointer', color: 'var(--rc-text-secondary)' }}
              onClick={() => navigate('/projects')}
            >
              Projects
            </span>
            {projectName && (
              <>
                <span className="rc-topbar-sep">/</span>
                <span className="rc-topbar-current">{projectName}</span>
              </>
            )}
          </div>
          <ServiceStatusBanner compact />
        </div>

        <div className="rc-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

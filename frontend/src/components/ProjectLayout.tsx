import { useCallback, useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useJobPolling } from '../hooks/useJobPolling';
import { downloadBlob } from './meta/exportUtils';
import {
  PROJECT_CONTENT_CHANGED_EVENT,
  type ProjectContentChangedDetail,
} from '../utils/projectEvents';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
  runtime_mode: string;
  archived: boolean;
};

type Dashboard = {
  project_id: string;
  counts: {
    papers: number;
    notes: number;
    meta_studies_current: number;
    references: number;
  };
};

const TABS: Array<{ to: string; label: string }> = [
  { to: 'research', label: 'Búsqueda' },
  { to: 'library', label: 'Biblioteca' },
  { to: 'reader', label: 'Lector' },
  { to: 'extraction', label: 'Extracción' },
  { to: 'matrix', label: 'Matrix' },
  { to: 'meta-runs', label: 'Meta-análisis' },
  { to: 'writing', label: 'Escritura' },
  { to: 'references', label: 'Referencias' },
];

const MORE_TABS: Array<{ to: string; label: string }> = [
  { to: 'artifacts', label: 'Artefactos' },
  { to: 'clinical-consults', label: 'Consultas clínicas' },
  { to: 'collaboration', label: 'Colaboración' },
];

export default function ProjectLayout() {
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const counts = dashboard?.counts;

  const exportJob = useJobPolling(exportJobId, {
    onCompleted: () => toast.success('Export listo', 'El ZIP está listo para descargar.'),
    onFailed: (s) => {
      const msg = s.error || 'Export ZIP falló';
      setError(msg);
      toast.error('Export falló', msg);
    },
  });

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data as Project);
      setError(null);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'No se pudo cargar el proyecto';
      setError(msg);
    }
  }, [projectId]);

  const loadDashboard = useCallback(async () => {
    if (!projectId) return;
    try {
      const response = await api.get(`/projects/${projectId}/dashboard`);
      setDashboard(response.data as Dashboard);
      setError(null);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'No se pudo cargar el proyecto';
      setError(msg);
    }
  }, [projectId]);

  useEffect(() => { void loadProject(); }, [loadProject]);
  useEffect(() => { void loadDashboard(); }, [loadDashboard, location.pathname]);

  useEffect(() => {
    if (!projectId) return undefined;
    const handleProjectUpdate = (event: Event) => {
      const detail = (event as CustomEvent<ProjectContentChangedDetail>).detail;
      if (detail?.projectId === projectId) void loadDashboard();
    };
    const handleFocus = () => void loadDashboard();
    window.addEventListener(PROJECT_CONTENT_CHANGED_EVENT, handleProjectUpdate as EventListener);
    window.addEventListener('focus', handleFocus);
    return () => {
      window.removeEventListener(PROJECT_CONTENT_CHANGED_EVENT, handleProjectUpdate as EventListener);
      window.removeEventListener('focus', handleFocus);
    };
  }, [loadDashboard, projectId]);

  async function startExportZip() {
    if (!projectId) return;
    setError(null);
    try {
      const r = await api.post(`/projects/${projectId}/export-zip`, {});
      setExportJobId(String((r.data as { job_id?: string })?.job_id || ''));
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Export ZIP falló');
    }
  }

  async function downloadZip() {
    if (!projectId || !exportJobId) return;
    setError(null);
    try {
      const filename = String((exportJob.status?.output as { filename?: string })?.filename || `project_export_${projectId}.zip`);
      const r = await api.get(`/projects/${projectId}/export-zip/${exportJobId}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, filename);
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Descarga ZIP falló');
    }
  }

  if (!projectId) return <div className="pg-card">Falta el id del proyecto</div>;

  if (error && !project) {
    return (
      <div className="pg-card pg-stack">
        <div style={{ color: 'var(--pg-danger)', fontSize: 14 }}>{String(error)}</div>
        <div>
          <Link to="/projects" className="pg-btn">← Volver a proyectos</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="pg-stack-lg pg-fade-in">
      {/* Project title bar */}
      <div className="pg-row-between">
        <div>
          <div className="pg-kicker" style={{ marginBottom: 6 }}>
            <Link to="/projects" style={{ color: 'inherit', textDecoration: 'none' }}>Proyectos</Link> / {project?.clinical_area || 'Sin área'}
          </div>
          <h1 className="pg-h1">{project?.title || 'Proyecto'}</h1>
          {project?.description ? (
            <p className="pg-muted" style={{ margin: '8px 0 0', maxWidth: 720, fontSize: 14 }}>
              {project.description}
            </p>
          ) : null}
        </div>
        <div className="pg-row">
          <div className="pg-row" style={{ gap: 6 }}>
            <span className="pg-badge pg-badge--info">{counts?.papers ?? 0} papers</span>
            <span className="pg-badge">{counts?.meta_studies_current ?? 0} estudios</span>
            <span className="pg-badge">{counts?.references ?? 0} ref.</span>
          </div>
          <button className="pg-btn pg-btn--sm" onClick={startExportZip} disabled={exportJob.isRunning}>
            {exportJob.isRunning ? `Exportando ${exportJob.status?.progress ?? 0}%` : 'Export ZIP'}
          </button>
          {exportJob.isDone && (
            <button className="pg-btn pg-btn--primary pg-btn--sm" onClick={downloadZip}>Descargar ZIP</button>
          )}
        </div>
      </div>

      {error && project ? (
        <div className="pg-card" style={{ borderColor: 'var(--pg-danger)', color: 'var(--pg-danger)', fontSize: 13 }}>
          {String(error)}
        </div>
      ) : null}

      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          gap: 4,
          borderBottom: '1px solid var(--pg-line)',
          overflowX: 'auto',
          paddingBottom: 0,
          position: 'relative',
        }}
      >
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `pg-btn pg-btn--ghost pg-btn--sm${isActive ? ' pg-btn--primary' : ''}`
            }
            style={({ isActive }) => ({
              borderRadius: '8px 8px 0 0',
              borderBottom: isActive ? '2px solid var(--pg-navy-800)' : '2px solid transparent',
              marginBottom: -1,
              textDecoration: 'none',
              flexShrink: 0,
              background: isActive ? 'transparent' : 'transparent',
              color: isActive ? 'var(--pg-navy-800)' : 'var(--pg-muted)',
              fontWeight: isActive ? 600 : 500,
            })}
          >
            {tab.label}
          </NavLink>
        ))}
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="pg-btn pg-btn--ghost pg-btn--sm"
            style={{ color: 'var(--pg-muted)' }}
            onClick={() => setMoreOpen((o) => !o)}
          >
            Más ▾
          </button>
          {moreOpen && (
            <div
              className="pg-dropdown-panel pg-fade-in"
              style={{ left: 'auto', right: 0, top: 40 }}
              onMouseLeave={() => setMoreOpen(false)}
            >
              {MORE_TABS.map((tab) => (
                <button
                  key={tab.to}
                  type="button"
                  style={{ display: 'block', width: '100%', textAlign: 'left', background: 'transparent', border: 'none', padding: '10px 12px', borderRadius: 8, cursor: 'pointer', color: 'var(--pg-text)', fontSize: 14 }}
                  onClick={() => {
                    setMoreOpen(false);
                    navigate(`/projects/${projectId}/${tab.to}`);
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Outlet content */}
      <Outlet />
    </div>
  );
}

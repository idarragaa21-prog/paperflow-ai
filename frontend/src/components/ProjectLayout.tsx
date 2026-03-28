import { useCallback, useEffect, useState } from 'react';
import { NavLink, Outlet, useParams, useNavigate, Link, useLocation } from 'react-router-dom';
import { downloadBlob } from './meta/exportUtils';
import { api } from '../services/api';
import { useJobPolling } from '../hooks/useJobPolling';
import { Breadcrumb } from './Breadcrumb';
import { useToast } from '../ui/Toast/ToastProvider';
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
    presentations: number;
    meta_studies_current: number;
    references: number;
  };
};

function Tab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) => `rc-nav-item ${isActive ? 'rc-nav-item--active' : ''}`}
      style={{ padding: '8px 10px', borderRadius: 10, whiteSpace: 'nowrap' }}
    >
      {label}
    </NavLink>
  );
}

export default function ProjectLayout() {
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportJob = useJobPolling(exportJobId, {
    onCompleted: () => toast.success('Export ready', 'ZIP is ready to download.'),
    onFailed: (s) => {
      const msg = s.error || 'Export ZIP failed';
      setError(msg);
      toast.error('Export failed', msg);
    },
  });

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    try {
      const response = await api.get(`/projects/${projectId}`);
      setProject(response.data as Project);
      setError(null);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to load project';
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
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to load project';
      setError(msg);
    }
  }, [projectId]);

  useEffect(() => {
    void loadProject();
  }, [loadProject]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard, location.pathname]);

  useEffect(() => {
    if (!projectId) return undefined;

    const handleProjectUpdate = (event: Event) => {
      const detail = (event as CustomEvent<ProjectContentChangedDetail>).detail;
      if (detail?.projectId === projectId) {
        void loadDashboard();
      }
    };
    const handleFocus = () => {
      void loadDashboard();
    };

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
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Export ZIP failed');
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
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Download ZIP failed');
    }
  }

  if (!projectId) return <div className="rc-error">Missing project id</div>;

  if (error && !project) {
    return (
      <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 24 }}>
        <div className="rc-error" style={{ fontSize: 14 }}>{String(error)}</div>
        <div>
          <Link to="/projects" className="rc-btn" style={{ textDecoration: 'none' }}>← Back to Projects</Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }} className="rc-page-enter">
      {/* Breadcrumb */}
      <Breadcrumb items={[
        { label: 'Projects', to: '/projects' },
        { label: project?.title || 'Project' },
      ]} />

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <h1 className="rc-page-title" style={{ marginBottom: 0 }}>{project?.title || 'Project'}</h1>
            {project?.clinical_area
              ? <div className="rc-subtitle">{project.clinical_area}</div>
              : <div className="rc-subtitle">Research project workspace</div>
            }
            <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                className="rc-btn rc-btn--primary rc-btn--sm"
                style={{ gap: 5 }}
                onClick={() => navigate(`/clinical?from_project=${projectId}`)}
              >
                <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10 2v4M8 4h4"/><rect x="3" y="6" width="14" height="12" rx="2"/><path d="M7 10h6M7 13h4"/></svg>
                Generate Clinical Sheet
                {(dashboard?.counts?.papers ?? 0) > 0 && (
                  <span style={{ background: 'rgba(255,255,255,0.25)', borderRadius: 6, padding: '1px 6px', fontSize: 10, fontWeight: 700 }}>
                    {dashboard!.counts.papers} paper{dashboard!.counts.papers !== 1 ? 's' : ''}
                  </span>
                )}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {[
              { label: 'Papers', value: dashboard?.counts?.papers ?? '—', color: 'var(--rc-info)' },
              { label: 'Notes', value: dashboard?.counts?.notes ?? '—', color: 'var(--rc-success)' },
              { label: 'Refs', value: dashboard?.counts?.references ?? '—', color: 'var(--rc-warning)' },
              { label: 'Extracted', value: dashboard?.counts?.meta_studies_current ?? '—', color: 'var(--rc-primary)' },
            ].map(s => (
              <div key={s.label} style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1,
                background: 'var(--rc-surface)', border: '1px solid var(--rc-border)',
                borderRadius: 10, padding: '7px 12px', boxShadow: 'var(--rc-shadow-xs)',
                minWidth: 52,
              }}>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 800, lineHeight: 1, color: s.color }}>{s.value}</span>
                <span style={{ fontSize: 10, color: 'var(--rc-muted)', fontWeight: 600 }}>{s.label}</span>
              </div>
            ))}

            <button className="rc-btn rc-btn--sm" onClick={startExportZip} style={{ gap: 5 }} disabled={exportJob.isRunning}>
              <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M10 3v10M5 13l5 5 5-5"/><path d="M3 17h14"/>
              </svg>
              {exportJob.isRunning ? `${exportJob.status?.progress ?? 0}%` : 'Export ZIP'}
            </button>

            {exportJob.isDone && (
              <button className="rc-btn rc-btn--primary rc-btn--sm" onClick={downloadZip}>⬇ Download</button>
            )}
          </div>
        </div>

        {error && project && (
          <div className="rc-error" style={{ fontSize: 12, marginTop: 8 }}>{String(error)}</div>
        )}
      </div>

      <div className="rc-card rc-tab-scroll" style={{ padding: 10 }}>
        <div className="rc-row" style={{ gap: 6, overflowX: 'auto', flexWrap: 'nowrap' }}>
          <Tab to={`/projects/${projectId}/research`} label="Research" />
          <Tab to={`/projects/${projectId}/reader`} label="Reader" />
          <Tab to={`/projects/${projectId}/library`} label="Library" />
          <Tab to={`/projects/${projectId}/meta`} label="Extraction" />
          <Tab to={`/projects/${projectId}/references`} label="References" />
          <Tab to={`/projects/${projectId}/drafts`} label="Drafts" />
          <Tab to={`/projects/${projectId}/analysis`} label="Analysis" />
          <Tab to={`/projects/${projectId}/screening`} label="Screening" />
          <Tab to={`/projects/${projectId}/collaboration`} label="Team" />
          <Tab to={`/projects/${projectId}/notes`} label="Notes" />
        </div>
      </div>

      <div className="rc-card">
        <Outlet />
      </div>
    </div>
  );
}

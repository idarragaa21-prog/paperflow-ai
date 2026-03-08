import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom';
import { downloadBlob } from './meta/exportUtils';
import { api } from '../services/api';

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

const TASKS = [
  {
    label: 'Discover',
    to: 'research',
    kicker: 'Step 1',
    copy: 'Search across scholarly sources and save the right papers.',
  },
  {
    label: 'Read & ask',
    to: 'reader',
    kicker: 'Step 2',
    copy: 'Read papers with grounded answers and page-level evidence.',
  },
  {
    label: 'Extract',
    to: 'meta',
    kicker: 'Step 3',
    copy: 'Turn PDFs into structured study records and review outputs.',
  },
  {
    label: 'Write',
    to: 'drafts',
    kicker: 'Step 4',
    copy: 'Draft literature summaries and evidence-backed sections.',
  },
  {
    label: 'Analyze',
    to: 'analysis',
    kicker: 'Step 5',
    copy: 'Run reproducible analyses and export final artifacts.',
  },
];

const MODULES = [
  { label: 'Discover', to: 'research' },
  { label: 'Read', to: 'reader' },
  { label: 'Library', to: 'library' },
  { label: 'Extract', to: 'meta' },
  { label: 'References', to: 'references' },
  { label: 'Write', to: 'drafts' },
  { label: 'Analyze', to: 'analysis' },
  { label: 'Review', to: 'screening' },
  { label: 'Team', to: 'collaboration' },
  { label: 'Notes', to: 'notes' },
];

function ModuleTab({ to, label }: { to: string; label: string }) {
  return (
    <NavLink to={to} end className={({ isActive }) => `rc-module-tab ${isActive ? 'rc-module-tab--active' : ''}`}>
      {label}
    </NavLink>
  );
}

export default function ProjectLayout() {
  const { projectId } = useParams();
  const location = useLocation();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentModule = useMemo(() => {
    const segment = location.pathname.split('/').filter(Boolean).pop() || 'research';
    return MODULES.find((module) => module.to === segment)?.label || 'Workspace';
  }, [location.pathname]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!projectId) return;
      setError(null);
      try {
        const [projectResponse, dashboardResponse] = await Promise.all([
          api.get(`/projects/${projectId}`),
          api.get(`/projects/${projectId}/dashboard`),
        ]);
        if (mounted) setProject(projectResponse.data as Project);
        if (mounted) setDashboard(dashboardResponse.data as Dashboard);
      } catch (e: any) {
        if (mounted) setError(e?.response?.data?.detail || 'Failed to load project');
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, [projectId]);

  async function startExportZip() {
    if (!projectId) return;
    setError(null);
    try {
      const r = await api.post(`/projects/${projectId}/export-zip`, {});
      const jid = String((r.data as any)?.job_id || '');
      setExportJobId(jid);
      setExportJobStatus({ status: 'queued', progress: 0, error: null });
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Export ZIP failed');
    }
  }

  async function downloadZip() {
    if (!projectId || !exportJobId) return;
    setError(null);
    try {
      const filename = String(exportJobStatus?.output?.filename || `project_export_${projectId}.zip`);
      const r = await api.get(`/projects/${projectId}/export-zip/${exportJobId}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, filename);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Download ZIP failed');
    }
  }

  useEffect(() => {
    if (!exportJobId) return;
    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${exportJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        const result = (r.data as any)?.result || {};
        const output = result?.output || result?.rq_result?.output;
        setExportJobStatus({ status, progress, error: err, output });
        if (status === 'completed' || status === 'failed') return;
      } catch (e: any) {
        setExportJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 2000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [exportJobId]);

  if (!projectId) return <div>Missing project id</div>;
  if (error) return <div style={{ color: 'crimson' }}>{String(error)}</div>;

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Workspace</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>{project?.title || 'Project'}</h1>
          <div className="rc-subtitle">
            {project?.description ||
              project?.clinical_area ||
              'Move from evidence discovery to writing and analysis inside one guided research workspace.'}
          </div>
          <div className="rc-help" style={{ marginTop: 12 }}>You are currently in <strong>{currentModule}</strong>. The recommended flow is Discover → Read → Extract → Write → Analyze.</div>
        </div>

        <div className="rc-stack" style={{ minWidth: 360, flex: 1 }}>
          <div className="rc-card">
            <div className="rc-card-title">Project snapshot</div>
            <div className="rc-kpi-strip">
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.papers ?? '—'}</strong><span>Papers saved</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.references ?? '—'}</strong><span>References</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.meta_studies_current ?? '—'}</strong><span>Extracted studies</span></div>
              <div className="rc-metric-tile"><strong>{dashboard?.counts?.notes ?? '—'}</strong><span>Notes</span></div>
            </div>
          </div>

          <div className="rc-next-step">
            <div className="rc-kicker">Current workspace mode</div>
            <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginTop: 4 }}>{project?.runtime_mode || 'local-only'}</div>
            <div className="rc-help" style={{ marginTop: 8 }}>Need a portable snapshot or handoff? Export the full workspace package below.</div>
            <div className="rc-row" style={{ marginTop: 12 }}>
              <button className="rc-btn" onClick={startExportZip}>Export workspace ZIP</button>
              {exportJobId && exportJobStatus?.status === 'completed' ? (
                <button className="rc-btn rc-btn--primary" onClick={downloadZip}>Download ZIP</button>
              ) : null}
            </div>
            {exportJobId ? <div className="rc-help" style={{ marginTop: 8 }}>{exportJobStatus?.status || 'queued'} · {exportJobStatus?.progress ?? 0}%</div> : null}
            {exportJobStatus?.error ? <div className="rc-error" style={{ marginTop: 8 }}>{String(exportJobStatus.error)}</div> : null}
          </div>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-toolbar" style={{ marginBottom: 12 }}>
          <div>
            <div className="rc-card-title" style={{ marginBottom: 4 }}>What do you want to do next?</div>
            <div className="rc-help">Use the guided tasks for the main workflow, then fall back to the full module navigation below.</div>
          </div>
          <Link className="rc-flow-link" to={`/projects/${projectId}/research`}>Return to discovery</Link>
        </div>
        <div className="rc-guided-grid">
          {TASKS.map((task, index) => (
            <Link key={task.to} to={`/projects/${projectId}/${task.to}`} className="rc-flow-card" style={{ color: 'inherit' }}>
              <div className={`rc-stage-label ${index % 2 === 0 ? 'rc-stage-label--teal' : 'rc-stage-label--warm'}`}>{task.kicker}</div>
              <h3>{task.label}</h3>
              <p>{task.copy}</p>
              <span className="rc-flow-link">Open {task.label.toLowerCase()}</span>
            </Link>
          ))}
        </div>
      </div>

      <div className="rc-card" style={{ padding: 14 }}>
        <div className="rc-kicker" style={{ marginBottom: 10 }}>All workspace areas</div>
        <div className="rc-module-tabs">
          {MODULES.map((module) => (
            <ModuleTab key={module.to} to={`/projects/${projectId}/${module.to}`} label={module.label} />
          ))}
        </div>
      </div>

      <div className="rc-card">
        <Outlet />
      </div>
    </div>
  );
}

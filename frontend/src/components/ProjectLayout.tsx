import { useEffect, useState } from 'react';
import { NavLink, Outlet, useParams, useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);

  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!projectId) return;
      setError(null);
      try {
        const [rp, rd] = await Promise.all([api.get(`/projects/${projectId}`), api.get(`/projects/${projectId}/dashboard`)]);
        if (mounted) setProject(rp.data as Project);
        if (mounted) setDashboard(rd.data as Dashboard);
      } catch (e: any) {
        if (mounted) setError(e?.response?.data?.detail || 'Failed to load project');
      }
    }
    load();
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

        if (status === 'completed' || status === 'failed') {
          return;
        }
      } catch (e: any) {
        setExportJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    poll();
    const t = window.setInterval(poll, 2000);
    return () => {
      stopped = true;
      window.clearInterval(t);
    };
  }, [exportJobId]);

  if (!projectId) return <div>Missing project id</div>;
  if (error) return <div style={{ color: 'crimson' }}>{String(error)}</div>;

  return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }} className="rc-page-enter">
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <h1 className="rc-page-title" style={{ marginBottom: 0 }}>{project?.title || 'Project'}</h1>
            {project?.clinical_area ? <div className="rc-subtitle">{project.clinical_area}</div> : <div className="rc-subtitle">Research project workspace</div>}
            {project?.runtime_mode ? <div className="rc-help">Runtime: {project.runtime_mode}</div> : null}
            <button
              className="rc-btn rc-btn--primary"
              style={{ marginTop: 8, padding: '7px 14px', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 6 }}
              onClick={() => navigate(`/clinical?from_project=${projectId}`)}
            >
              🩺 Generate Clinical Sheet
              {dashboard?.counts?.papers ? (
                <span style={{ background: 'rgba(255,255,255,0.25)', borderRadius: 8, padding: '1px 7px', fontSize: 11, fontWeight: 700 }}>
                  {dashboard.counts.papers} paper{dashboard.counts.papers !== 1 ? 's' : ''}
                </span>
              ) : null}
            </button>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {[
              { label: 'Papers', value: dashboard?.counts?.papers ?? '—', icon: '📄', color: 'var(--rc-info)' },
              { label: 'Notes', value: dashboard?.counts?.notes ?? '—', icon: '📝', color: 'var(--rc-success)' },
              { label: 'References', value: dashboard?.counts?.references ?? '—', icon: '🔗', color: 'var(--rc-warning)' },
              { label: 'Extracted', value: dashboard?.counts?.meta_studies_current ?? '—', icon: '🔬', color: 'var(--rc-primary)' },
            ].map(s => (
              <div key={s.label} style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1,
                background: 'var(--rc-surface)', border: '1px solid var(--rc-border)',
                borderRadius: 10, padding: '8px 14px', boxShadow: 'var(--rc-shadow-xs)',
              }}>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 800, lineHeight: 1, color: 'var(--rc-text)' }}>{s.value}</span>
                <span style={{ fontSize: 10, color: 'var(--rc-muted)', fontWeight: 600 }}>{s.label}</span>
              </div>
            ))}
            <button className="rc-btn rc-btn--sm" onClick={startExportZip} style={{ gap: 5 }}>
              <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10 3v10M5 13l5 5 5-5"/><path d="M3 17h14"/></svg>
              Export ZIP
            </button>
            {exportJobId ? <div className="rc-help">{exportJobStatus?.status || 'queued'} · {exportJobStatus?.progress ?? 0}%</div> : null}
            {exportJobId && exportJobStatus?.status === 'completed' ? (
              <button className="rc-btn rc-btn--primary rc-btn--sm" onClick={downloadZip}>⬇ Download</button>
            ) : null}
            {exportJobStatus?.error ? <div className="rc-error" style={{ fontSize: 12 }}>{String(exportJobStatus.error)}</div> : null}
          </div>
        </div>
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
          <Tab to={`/projects/${projectId}/notes`} label="Notes" />
        </div>
      </div>

      <div className="rc-card">
        <Outlet />
      </div>
    </div>
  );
}

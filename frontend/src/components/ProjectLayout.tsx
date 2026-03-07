import { useEffect, useState } from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
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
      style={{ padding: '8px 10px', borderRadius: 10 }}
    >
      {label}
    </NavLink>
  );
}

export default function ProjectLayout() {
  const { projectId } = useParams();
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div>
            <h1 className="rc-page-title" style={{ marginBottom: 0 }}>{project?.title || 'Project'}</h1>
            {project?.clinical_area ? <div className="rc-subtitle">{project.clinical_area}</div> : <div className="rc-subtitle">Research project workspace</div>}
            {project?.runtime_mode ? <div className="rc-help">Runtime: {project.runtime_mode}</div> : null}
          </div>

          <div className="rc-card" style={{ minWidth: 360 }}>
            <div className="rc-card-title">Dashboard</div>
            <div className="rc-row" style={{ gap: 10 }}>
              <span className="rc-badge">Papers: <b>{dashboard?.counts?.papers ?? '—'}</b></span>
              <span className="rc-badge">Notes: <b>{dashboard?.counts?.notes ?? '—'}</b></span>
              <span className="rc-badge">Refs: <b>{dashboard?.counts?.references ?? '—'}</b></span>
              <span className="rc-badge">Extracted: <b>{dashboard?.counts?.meta_studies_current ?? '—'}</b></span>
            </div>

            <div style={{ height: 10 }} />

            <div className="rc-row">
              <button className="rc-btn" onClick={startExportZip}>Export ZIP</button>
              {exportJobId ? <div className="rc-help">{exportJobStatus?.status || 'queued'} · {exportJobStatus?.progress ?? 0}%</div> : null}
              {exportJobId && exportJobStatus?.status === 'completed' ? (
                <button className="rc-btn rc-btn--primary" onClick={downloadZip}>Download ZIP</button>
              ) : null}
            </div>
            {exportJobStatus?.error ? <div className="rc-error" style={{ fontSize: 12, marginTop: 8 }}>{String(exportJobStatus.error)}</div> : null}
          </div>
        </div>
      </div>

      <div className="rc-card" style={{ padding: 10 }}>
        <div className="rc-row" style={{ gap: 6 }}>
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

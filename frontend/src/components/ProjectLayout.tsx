import { useState } from 'react';
import { NavLink, Outlet, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { downloadBlob } from './meta/exportUtils';
import { api } from '../services/api';
import { Skeleton } from '../ui/Skeleton/Skeleton';

type Project = {
  id: string;
  title: string;
  description?: string | null;
  clinical_area?: string | null;
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
      className={({ isActive }) => `rc-tab${isActive ? ' rc-tab--active' : ''}`}
    >
      {label}
    </NavLink>
  );
}

function StatChip({ label, value }: { label: string; value: number | '—' }) {
  return (
    <div className="rc-stat-chip">
      <span className="rc-stat-chip-value">{value}</span>
      <span className="rc-stat-chip-label">{label}</span>
    </div>
  );
}

// Clinical sheet icon SVG
function ClinicalIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2v4M8 4h4"/>
      <rect x="3" y="6" width="14" height="12" rx="2"/>
      <path d="M7 11h6M7 14h4"/>
    </svg>
  );
}

export default function ProjectLayout() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [exportJobId, setExportJobId] = useState<string | null>(null);

  // ── Project + dashboard data ──────────────────────────────────────────────
  const { data: project, isLoading: projLoading, error: projError } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data as Project,
    enabled: !!projectId,
    staleTime: 30_000,
  });

  const { data: dashboard } = useQuery<Dashboard>({
    queryKey: ['project-dashboard', projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/dashboard`)).data as Dashboard,
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // ── Export job polling ────────────────────────────────────────────────────
  const { data: exportJob } = useQuery({
    queryKey: ['job', exportJobId],
    queryFn: async () => {
      const r = await api.get(`/jobs/${exportJobId}`);
      return r.data as { status: string; progress_percent: number; error?: string | null; result?: any };
    },
    enabled: !!exportJobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === 'completed' || s === 'failed' ? false : 2000;
    },
  });

  // ── Export mutation ───────────────────────────────────────────────────────
  const exportMut = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/export-zip`, {})).data,
    onSuccess: (data: any) => {
      setExportJobId(String(data?.job_id || ''));
    },
  });

  async function downloadZip() {
    if (!projectId || !exportJobId) return;
    const filename = String(exportJob?.result?.output?.filename || `project_export_${projectId}.zip`);
    const r = await api.get(`/projects/${projectId}/export-zip/${exportJobId}/download`, { responseType: 'blob' });
    downloadBlob(r.data as Blob, filename);
  }

  if (!projectId) return <div className="rc-error-card">Missing project ID.</div>;

  if (projError) {
    const msg = (projError as any)?.response?.data?.detail || 'Failed to load project';
    return (
      <div className="rc-error-card">
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14h.01"/></svg>
        {msg}
      </div>
    );
  }

  const counts = dashboard?.counts;
  const exportStatus = exportJob?.status;
  const exportRunning = !!exportJobId && exportStatus !== 'completed' && exportStatus !== 'failed';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }} className="rc-page-enter">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {projLoading ? (
            <>
              <Skeleton height={26} width="52%" radius={8} />
              <div style={{ height: 8 }} />
              <Skeleton height={14} width="32%" radius={6} />
            </>
          ) : (
            <>
              <h1 className="rc-page-title" style={{ marginBottom: 0 }}>{project?.title || 'Project'}</h1>
              <div className="rc-subtitle">
                {project?.clinical_area || 'Research project workspace'}
              </div>
            </>
          )}
          <button
            className="rc-btn rc-btn--primary"
            style={{ marginTop: 10, padding: '7px 14px', fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 6 }}
            onClick={() => navigate(`/clinical?from_project=${projectId}`)}
          >
            <ClinicalIcon />
            Generate Clinical Sheet
            {counts?.papers ? (
              <span style={{ background: 'rgba(255,255,255,0.22)', borderRadius: 6, padding: '1px 7px', fontSize: 11, fontWeight: 700 }}>
                {counts.papers} paper{counts.papers !== 1 ? 's' : ''}
              </span>
            ) : null}
          </button>
        </div>

        {/* Stats + Export */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <StatChip label="Papers" value={counts?.papers ?? '—'} />
          <StatChip label="Notes" value={counts?.notes ?? '—'} />
          <StatChip label="Refs" value={counts?.references ?? '—'} />
          <StatChip label="Extracted" value={counts?.meta_studies_current ?? '—'} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-end' }}>
            <button
              className="rc-btn rc-btn--sm"
              onClick={() => exportMut.mutate()}
              disabled={exportRunning || exportMut.isPending}
              style={{ gap: 5 }}
            >
              <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M10 3v10M5 13l5 5 5-5"/><path d="M3 17h14"/>
              </svg>
              {exportRunning ? `Exporting… ${exportJob?.progress_percent ?? 0}%` : 'Export ZIP'}
            </button>
            {exportStatus === 'completed' && (
              <button className="rc-btn rc-btn--sm rc-btn--primary" onClick={downloadZip} style={{ gap: 5 }}>
                <svg width="12" height="12" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M10 3v10M5 13l5 5 5-5"/><path d="M3 17h14"/>
                </svg>
                Download ZIP
              </button>
            )}
            {exportJob?.error && (
              <div className="rc-error" style={{ fontSize: 12 }}>{String(exportJob.error)}</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Tab navigation ───────────────────────────────────────────────── */}
      <div className="rc-card" style={{ padding: '8px 10px' }}>
        <nav className="rc-tab-nav">
          <Tab to={`/projects/${projectId}/research`} label="Research" />
          <Tab to={`/projects/${projectId}/reader`} label="Reader" />
          <Tab to={`/projects/${projectId}/library`} label="Library" />
          <Tab to={`/projects/${projectId}/meta`} label="Extraction" />
          <Tab to={`/projects/${projectId}/references`} label="References" />
          <Tab to={`/projects/${projectId}/drafts`} label="Drafts" />
          <Tab to={`/projects/${projectId}/presentations`} label="Presentations" />
          <Tab to={`/projects/${projectId}/analysis`} label="Analysis" />
          <Tab to={`/projects/${projectId}/screening`} label="Screening" />
          <Tab to={`/projects/${projectId}/notes`} label="Notes" />
        </nav>
      </div>

      {/* ── Page content ─────────────────────────────────────────────────── */}
      <div className="rc-card">
        <Outlet context={{ project, dashboard, projectId }} />
      </div>
    </div>
  );
}

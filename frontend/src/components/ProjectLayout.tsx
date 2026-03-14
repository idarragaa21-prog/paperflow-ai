import {
  BarChart2, BookOpen, CheckSquare, ChevronRight,
  Download, FileText, FlaskConical, Library,
  Quote, Search, StickyNote
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { api } from '../services/api';
import { downloadBlob } from './meta/exportUtils';

type Project = {
  id: string; title: string; description?: string | null;
  clinical_area?: string | null; runtime_mode: string; archived: boolean;
};
type Dashboard = {
  project_id: string;
  counts: { papers: number; notes: number; presentations: number; meta_studies_current: number; references: number };
};

function Tab({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) => `rc-tab ${isActive ? 'rc-tab--active' : ''}`}
    >
      {icon}
      {label}
    </NavLink>
  );
}

export default function ProjectLayout() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject]   = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null; output?: any } | null>(null);

  const [bannerDismissed, setBannerDismissed] = useState<boolean>(() => {
    try { return localStorage.getItem(`pf_onboard_${projectId}`) === '1'; } catch { return true; }
  });
  function dismissBanner() {
    try { localStorage.setItem(`pf_onboard_${projectId}`, '1'); } catch {}
    setBannerDismissed(true);
  }
  const showOnboardBanner =
    !bannerDismissed && dashboard !== null &&
    dashboard.counts.papers === 0 && dashboard.counts.notes === 0;

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!projectId) return;
      setError(null);
      try {
        const [rp, rd] = await Promise.all([
          api.get(`/projects/${projectId}`),
          api.get(`/projects/${projectId}/dashboard`),
        ]);
        if (mounted) { setProject(rp.data as Project); setDashboard(rd.data as Dashboard); }
      } catch (e: any) {
        if (mounted) setError(e?.response?.data?.detail || 'Failed to load project');
      }
    }
    load();
    return () => { mounted = false; };
  }, [projectId]);

  async function startExportZip() {
    if (!projectId) return;
    try {
      const r = await api.post(`/projects/${projectId}/export-zip`, {});
      const jid = String((r.data as any)?.job_id || '');
      setExportJobId(jid);
      setExportJobStatus({ status: 'queued', progress: 0 });
    } catch (e: any) { setError(e?.response?.data?.detail || 'Export failed'); }
  }
  async function downloadZip() {
    if (!projectId || !exportJobId) return;
    const filename = String(exportJobStatus?.output?.filename || `project_export_${projectId}.zip`);
    const r = await api.get(`/projects/${projectId}/export-zip/${exportJobId}/download`, { responseType: 'blob' });
    downloadBlob(r.data as Blob, filename);
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
        const result = (r.data as any)?.result || {};
        const output = result?.output || result?.rq_result?.output;
        setExportJobStatus({ status, progress, output });
        if (status === 'completed' || status === 'failed') return;
      } catch {}
    }
    poll();
    const t = window.setInterval(poll, 2000);
    return () => { stopped = true; window.clearInterval(t); };
  }, [exportJobId]);

  if (!projectId) return (
    <div style={{ padding: 32 }}>
      <div className="rc-error" style={{ marginBottom: 12 }}>Missing project id</div>
      <button className="rc-btn" onClick={() => navigate('/projects')}>← Back to projects</button>
    </div>
  );
  if (error) return (
    <div style={{ padding: 32, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="rc-error">{error}</div>
      <button className="rc-btn" style={{ width: 'fit-content' }} onClick={() => navigate('/projects')}>← Back to projects</button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0, margin: '-24px', minHeight: '100%' }}>

      {/* ── Project Header ── */}
      <div style={{
        background: 'var(--rc-surface-1)',
        borderBottom: '1px solid var(--rc-border)',
        padding: '20px 24px 0',
      }}>
        {/* Title row */}
        <div className="rc-project-header" style={{ paddingBottom: 16 }}>
          <div className="rc-project-meta">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="rc-page-title">{project?.title || <span className="rc-skeleton" style={{ width: 220, height: 24, display: 'inline-block', borderRadius: 6 }} />}</h1>
              {project?.archived && <span className="rc-tag rc-tag--slate">archived</span>}
            </div>
            <div className="rc-project-tags">
              {project?.clinical_area && <span className="rc-tag rc-tag--indigo">{project.clinical_area}</span>}
              {project?.runtime_mode  && <span className="rc-tag rc-tag--slate">{project.runtime_mode}</span>}
            </div>
          </div>

          {/* Stats + actions */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 }}>
              {[
                { label: 'Papers',    value: dashboard?.counts.papers },
                { label: 'Notes',     value: dashboard?.counts.notes },
                { label: 'Refs',      value: dashboard?.counts.references },
                { label: 'Extracted', value: dashboard?.counts.meta_studies_current },
              ].map(({ label, value }) => (
                <div key={label} className="rc-stat">
                  <span className="rc-stat-value">{value ?? '—'}</span>
                  <span className="rc-stat-label">{label}</span>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <button className="rc-btn" style={{ fontSize: 12 }} onClick={startExportZip}>
                <Download size={13} /> Export ZIP
              </button>
              {exportJobId && exportJobStatus?.status !== 'completed' && (
                <div className="rc-help" style={{ textAlign: 'center' }}>{exportJobStatus?.status} {exportJobStatus?.progress ?? 0}%</div>
              )}
              {exportJobStatus?.status === 'completed' && (
                <button className="rc-btn rc-btn--primary" style={{ fontSize: 12 }} onClick={downloadZip}>
                  <Download size={13} /> Download
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Onboarding banner */}
        {showOnboardBanner && (
          <div style={{
            margin: '0 0 0 0',
            padding: '10px 14px',
            background: 'var(--rc-primary-weak)',
            border: '1px solid var(--rc-primary-border)',
            borderRadius: '10px 10px 0 0',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12,
          }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--rc-primary)' }}>🚀 Get started:</span>
              {[
                { label: '1 · Search', tab: 'research' },
                { label: '2 · Download PDFs', tab: 'library' },
                { label: '3 · Extract data', tab: 'meta' },
                { label: '4 · Write', tab: 'drafts' },
              ].map(({ label, tab }) => (
                <a key={tab} href={`/projects/${projectId}/${tab}`} style={{ textDecoration: 'none' }}>
                  <span className="rc-tag rc-tag--indigo" style={{ cursor: 'pointer', fontSize: 11 }}>
                    {label} <ChevronRight size={10} />
                  </span>
                </a>
              ))}
            </div>
            <button className="rc-btn rc-btn--ghost" style={{ fontSize: 11, padding: '3px 8px' }} onClick={dismissBanner}>
              Got it ✓
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="rc-tabs-bar">
          <Tab to={`/projects/${projectId}/research`}  label="Research"   icon={<Search      size={13} />} />
          <Tab to={`/projects/${projectId}/reader`}    label="Reader"     icon={<BookOpen    size={13} />} />
          <Tab to={`/projects/${projectId}/library`}   label="Library"    icon={<Library     size={13} />} />
          <Tab to={`/projects/${projectId}/meta`}      label="Extraction" icon={<FlaskConical size={13} />} />
          <Tab to={`/projects/${projectId}/references`} label="References" icon={<Quote      size={13} />} />
          <Tab to={`/projects/${projectId}/drafts`}    label="Drafts"     icon={<FileText    size={13} />} />
          <Tab to={`/projects/${projectId}/analysis`}  label="Analysis"   icon={<BarChart2   size={13} />} />
          <Tab to={`/projects/${projectId}/screening`} label="Screening"  icon={<CheckSquare size={13} />} />
          <Tab to={`/projects/${projectId}/notes`}     label="Notes"      icon={<StickyNote  size={13} />} />
        </div>
      </div>

      {/* ── Page Content ── */}
      <div style={{ padding: 24, flex: 1 }}>
        <Outlet />
      </div>
    </div>
  );
}

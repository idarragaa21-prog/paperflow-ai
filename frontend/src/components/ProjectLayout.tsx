import { useCallback, useEffect, useState } from 'react';
import { NavLink, Outlet, useParams, useNavigate, Link, useLocation } from 'react-router-dom';
import { downloadBlob } from './meta/exportUtils';
import { api } from '../services/api';
import { useJobPolling } from '../hooks/useJobPolling';
import { Breadcrumb } from './Breadcrumb';
import { useToast } from '../ui/Toast/ToastProvider';
import { useProjectStore } from '../store/projectStore';
import {
  getProjectNextAction,
  getWorkflowStages,
  getWorkflowCompletion,
  InsightCard,
  PageHero,
  ProjectWorkflowRail,
  type WorkflowStageKey,
} from './WorkflowPrimitives';
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

function currentStage(pathname: string): WorkflowStageKey | undefined {
  if (pathname.includes('/library') || pathname.includes('/papers')) return 'library';
  if (pathname.includes('/reader')) return 'reader';
  if (pathname.includes('/meta')) return 'extract';
  if (pathname.includes('/drafts')) return 'write';
  if (pathname.includes('/analysis')) return 'analysis';
  if (pathname.includes('/research') || pathname.includes('/search')) return 'research';
  return undefined;
}

export default function ProjectLayout() {
  const { projectId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const toast = useToast();
  const setActiveProjectId = useProjectStore((s) => s.setActiveProjectId);
  const [project, setProject] = useState<Project | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const counts = dashboard?.counts;
  const stage = currentStage(location.pathname);
  const stageInfo = getWorkflowStages(projectId || '', counts, stage).find((item) => item.key === stage);

  useEffect(() => {
    setActiveProjectId(projectId ?? null);
    return () => setActiveProjectId(null);
  }, [projectId, setActiveProjectId]);

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

  const nextAction = getProjectNextAction(projectId, counts);
  const completion = getWorkflowCompletion(counts);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }} className="rc-page-enter">
      <Breadcrumb items={[
        { label: 'Projects', to: '/projects' },
        { label: project?.title || 'Project' },
      ]} />

      <PageHero
        eyebrow="Project workflow"
        title={project?.title || 'Project'}
        subtitle={project?.clinical_area || 'Move from evidence discovery to extraction, writing and final analysis in one continuous workspace.'}
        metrics={[
          { label: 'workflow completion', value: `${completion}%`, tone: 'primary' },
          { label: 'papers', value: counts?.papers ?? '—', tone: 'success' },
          { label: 'studies', value: counts?.meta_studies_current ?? '—', tone: 'warning' },
          { label: 'references', value: counts?.references ?? '—', tone: 'neutral' },
        ]}
        actions={(
          <>
            <Link className="rc-btn rc-btn--primary" style={{ textDecoration: 'none' }} to={nextAction.to}>
              {nextAction.label}
            </Link>
            <button
              className="rc-btn"
              style={{ gap: 5 }}
              onClick={() => navigate(`/clinical?from_project=${projectId}`)}
            >
              Generate Clinical Sheet
            </button>
            <button className="rc-btn" onClick={startExportZip} disabled={exportJob.isRunning}>
              {exportJob.isRunning ? `${exportJob.status?.progress ?? 0}%` : 'Export project ZIP'}
            </button>
            {exportJob.isDone && (
              <button className="rc-btn rc-btn--primary" onClick={downloadZip}>Download ZIP</button>
            )}
          </>
        )}
        aside={(
          <InsightCard
            eyebrow="Next recommended action"
            title={nextAction.label}
            body={nextAction.description}
            tone="primary"
            action={<Link className="rc-btn rc-btn--primary rc-btn--sm" style={{ textDecoration: 'none' }} to={nextAction.to}>Continue</Link>}
          />
        )}
      />

      {error && project ? <div className="rc-error" style={{ fontSize: 12 }}>{String(error)}</div> : null}

      <ProjectWorkflowRail projectId={projectId} counts={counts} current={stage} />

      <div className="rc-card" style={{ display: 'flex', justifyContent: 'space-between', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div className="rc-kicker" style={{ marginBottom: 0 }}>Workspace support</div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em' }}>
            {stageInfo ? `Current stage: ${stageInfo.label}` : 'Supporting tools around the main workflow'}
          </div>
          <div className="rc-help" style={{ maxWidth: 640 }}>
            {stageInfo?.description || nextAction.description}
          </div>
        </div>
        <div className="rc-support-nav">
          <NavLink to={`/projects/${projectId}/literature-review`} className="rc-support-pill">Compare Literature</NavLink>
          <NavLink to={`/projects/${projectId}/references`} className="rc-support-pill">References</NavLink>
          <NavLink to={`/projects/${projectId}/screening`} className="rc-support-pill">Screening</NavLink>
          <NavLink to={`/projects/${projectId}/collaboration`} className="rc-support-pill">Team</NavLink>
          <NavLink to={`/projects/${projectId}/notes`} className="rc-support-pill">Notes</NavLink>
        </div>
      </div>

      <Outlet />
    </div>
  );
}

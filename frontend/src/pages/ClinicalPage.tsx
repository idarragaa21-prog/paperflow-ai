import { useMemo, useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { Breadcrumb } from '../components/Breadcrumb';
import type { Project, ClinicalSheetRow } from '../types/api';

export default function ClinicalPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const fromProject = searchParams.get('from_project');

  // Form state
  const [projectId, setProjectId] = useState<string>(fromProject || '');
  const [topic, setTopic] = useState('');
  const [context, setContext] = useState('');
  const [objective, setObjective] = useState<'clinical_decision' | 'teaching' | 'presentation' | 'quick_review'>('clinical_decision');
  const [level, setLevel] = useState<'R1' | 'R3' | 'fellow' | 'specialist'>('specialist');
  const [focus, setFocus] = useState<'surgical' | 'conservative' | 'diagnostic' | 'rehab' | 'complications' | 'complete'>('complete');
  const [region, setRegion] = useState('');
  const [maxLength, setMaxLength] = useState<'brief' | 'standard' | 'exhaustive'>('standard');
  const [useProjectPapers, setUseProjectPapers] = useState(true);
  const [searchOnline, setSearchOnline] = useState(true);
  const [advanced, setAdvanced] = useState(false);

  // Job polling
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<{ status: string; progress: number; error?: string | null; sheet_id?: string | null } | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  const canGenerate = useMemo(() => topic.trim().length > 0, [topic]);
  const sheetsKey = useMemo(() => ['clinical-sheets', projectId], [projectId]);

  // ── Projects query ────────────────────────────────────────────────────────
  const { data: projects = [] } = useQuery<Pick<Project, 'id' | 'title' | 'clinical_area'>[]>({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const r = await api.get('/projects');
      return (r.data as Project[]).filter(p => !p.archived).map(p => ({ id: p.id, title: p.title, clinical_area: p.clinical_area }));
    },
    staleTime: 60_000,
  });

  const selectedProject = projects.find(p => p.id === projectId);

  // ── Paper count for selected project ─────────────────────────────────────
  const { data: projectPaperCount } = useQuery<number>({
    queryKey: ['project-paper-count', projectId],
    queryFn: async () => {
      if (!projectId) return 0;
      const r = await api.get(`/projects/${projectId}/dashboard`);
      return (r.data as { counts?: { papers?: number } })?.counts?.papers ?? 0;
    },
    enabled: !!projectId,
    staleTime: 60_000,
  });

  // ── Sheets query ──────────────────────────────────────────────────────────
  const { data: sheets = [], isLoading: sheetsLoading, error: sheetsError } = useQuery<ClinicalSheetRow[]>({
    queryKey: sheetsKey,
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (projectId) params.project_id = projectId;
      const r = await api.get('/clinical/sheets', { params });
      return r.data as ClinicalSheetRow[];
    },
  });

  // ── Generate mutation ─────────────────────────────────────────────────────
  const generateMut = useMutation({
    mutationFn: async () => {
      const r = await api.post('/clinical/query', {
        topic: topic.trim(),
        project_id: projectId || null,
        context: context.trim() || null,
        objective, level, focus,
        region: region.trim() || null,
        max_length: maxLength,
        use_project_papers: useProjectPapers,
        search_online: searchOnline,
      });
      return r.data as { job_id?: string };
    },
    onSuccess: (data) => {
      if (data.job_id) {
        setJobId(data.job_id);
        setJobStatus({ status: 'queued', progress: 0, error: null, sheet_id: null });
        setGenError(null);
      }
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Generation failed';
      setGenError(msg);
    },
  });

  // ── Job polling ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${jobId}`);
        const data = r.data as Record<string, unknown>;
        const status = String(data?.status || 'unknown');
        const progress = Number(data?.progress_percent || 0);
        const err = (data?.error as string) || null;
        const sheet_id = (data?.result as Record<string, unknown>)?.sheet_id as string | null || null;
        setJobStatus({ status, progress, error: err, sheet_id });
        if (status === 'completed') {
          qc.invalidateQueries({ queryKey: sheetsKey });
          setJobId(null);
          if (sheet_id) navigate(`/clinical/sheets/${sheet_id}`);
        }
        if (status === 'failed') {
          setJobId(null);
          setGenError(err || 'Generation failed');
        }
      } catch (e: unknown) {
        setJobStatus({ status: 'polling_error', progress: 0, error: (e as Error)?.message || 'Polling failed' });
      }
    }
    poll();
    const t = window.setInterval(poll, 4000);
    return () => { stopped = true; window.clearInterval(t); };
  }, [jobId, navigate, qc, sheetsKey]);

  const errorMsg = genError || (sheetsError as Error | null)?.message;

  const breadcrumbItems = fromProject && selectedProject
    ? [
        { label: 'Projects', to: '/projects' },
        { label: selectedProject.title, to: `/projects/${fromProject}/research` },
        { label: 'Clinical Sheet' },
      ]
    : [{ label: 'Clinical' }];

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 980 }}>
      <Breadcrumb items={breadcrumbItems} />

      <div>
        <h1 className="rc-page-title">Clinical Sheets</h1>
        <div className="rc-subtitle">Generate evidence-based clinical summaries with traceable citations, UpToDate-style.</div>
      </div>

      {errorMsg && <div className="rc-error">{String(errorMsg)}</div>}

      {/* ── Project context banner ── */}
      {projectId && selectedProject && (
        <div className="rc-card" style={{ background: 'rgba(79,70,229,0.06)', border: '1px solid rgba(79,70,229,0.15)', padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 13 }}>
              <span style={{ color: 'var(--rc-muted)' }}>Using papers from</span>{' '}
              <Link to={`/projects/${projectId}/library`} style={{ fontWeight: 700, color: 'var(--rc-primary)', textDecoration: 'none' }}>
                {selectedProject.title}
              </Link>
              {(projectPaperCount ?? 0) > 0 && (
                <span style={{ color: 'var(--rc-muted)', marginLeft: 6 }}>
                  · {projectPaperCount} paper{projectPaperCount !== 1 ? 's' : ''} available
                </span>
              )}
            </div>
            <button
              className="rc-btn rc-btn--sm rc-btn--ghost"
              onClick={() => setProjectId('')}
              style={{ fontSize: 11 }}
            >
              Remove project
            </button>
          </div>
        </div>
      )}

      {/* ── Generator form ── */}
      <div className="rc-card">
        <div className="rc-card-title">New Clinical Sheet</div>

        {/* Project selector */}
        {projects.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div className="rc-kicker">Project (optional) — use its papers as evidence</div>
            <select className="rc-select" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">(none — online sources only)</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.title}{p.clinical_area ? ` · ${p.clinical_area}` : ''}</option>
              ))}
            </select>
          </div>
        )}

        <div className="rc-kicker">Topic *</div>
        <textarea
          className="rc-textarea"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Fifth metatarsal stress fracture — diagnosis and treatment"
          style={{ minHeight: 90 }}
        />

        <div style={{ height: 10 }} />
        <button className="rc-btn rc-btn--ghost" onClick={() => setAdvanced(v => !v)} style={{ fontSize: 12 }}>
          {advanced ? '▲ Hide advanced options' : '▼ Show advanced options'}
        </button>

        {advanced && (
          <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <div className="rc-kicker">Region / anatomy</div>
              <input className="rc-input" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="e.g. foot/ankle" />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div className="rc-kicker">Clinical context</div>
              <textarea
                className="rc-textarea"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Age, sport, comorbidities, clinical scenario…"
                style={{ minHeight: 72 }}
              />
            </div>
            <div>
              <div className="rc-kicker">Objective</div>
              <select className="rc-select" value={objective} onChange={(e) => setObjective(e.target.value as typeof objective)}>
                <option value="clinical_decision">Clinical decision</option>
                <option value="teaching">Teaching</option>
                <option value="presentation">Presentation</option>
                <option value="quick_review">Quick review</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Level</div>
              <select className="rc-select" value={level} onChange={(e) => setLevel(e.target.value as typeof level)}>
                <option value="R1">R1</option>
                <option value="R3">R3</option>
                <option value="fellow">Fellow</option>
                <option value="specialist">Specialist</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Focus</div>
              <select className="rc-select" value={focus} onChange={(e) => setFocus(e.target.value as typeof focus)}>
                <option value="complete">Complete</option>
                <option value="diagnostic">Diagnostic</option>
                <option value="conservative">Conservative</option>
                <option value="surgical">Surgical</option>
                <option value="rehab">Rehabilitation</option>
                <option value="complications">Complications</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Length</div>
              <select className="rc-select" value={maxLength} onChange={(e) => setMaxLength(e.target.value as typeof maxLength)}>
                <option value="brief">Brief</option>
                <option value="standard">Standard</option>
                <option value="exhaustive">Exhaustive</option>
              </select>
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={useProjectPapers} onChange={(e) => setUseProjectPapers(e.target.checked)} />
              Use project papers
            </label>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' }}>
              <input type="checkbox" checked={searchOnline} onChange={(e) => setSearchOnline(e.target.checked)} />
              Search online evidence
            </label>
          </div>
        )}

        <div style={{ height: 14 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <button
            className="rc-btn rc-btn--primary"
            disabled={!canGenerate || generateMut.isPending || Boolean(jobId)}
            onClick={() => generateMut.mutate()}
          >
            {jobId ? 'Generating…' : generateMut.isPending ? 'Starting…' : 'Generate Clinical Sheet'}
          </button>
          {projectId && (projectPaperCount ?? 0) > 0 && !jobId && !generateMut.isPending && (
            <div className="rc-help">
              Will use {projectPaperCount} paper{projectPaperCount !== 1 ? 's' : ''} from project + online search
            </div>
          )}
        </div>

        {jobStatus && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span className="rc-help">
                {jobStatus.status === 'queued' ? 'Queued' :
                 jobStatus.status === 'started' ? 'Running' :
                 jobStatus.status === 'polling_error' ? 'Connection error' :
                 jobStatus.status}
              </span>
              <span className="rc-help">· {jobStatus.progress}%</span>
              {jobStatus.error && <span className="rc-error"> · {String(jobStatus.error)}</span>}
            </div>
            <div className="rc-progress">
              <div style={{ width: `${Math.max(5, Math.min(100, jobStatus.progress))}%` }} />
            </div>
            {jobStatus.status === 'started' && jobStatus.progress < 80 && (
              <div className="rc-help" style={{ marginTop: 6 }}>
                This may take 30–120 seconds depending on the number of papers and sources.
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Sheets list ── */}
      <div className="rc-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div className="rc-card-title" style={{ marginBottom: 0 }}>Recent Sheets</div>
          <button
            className="rc-btn rc-btn--sm rc-btn--ghost"
            onClick={() => qc.invalidateQueries({ queryKey: sheetsKey })}
            disabled={sheetsLoading}
          >
            {sheetsLoading ? '…' : '↻ Refresh'}
          </button>
        </div>

        {sheets.length === 0 && !sheetsLoading ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--rc-muted)', fontSize: 13 }}>
            No sheets yet. Generate your first one above.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sheets.map(s => (
              <button
                key={s.id}
                onClick={() => navigate(`/clinical/sheets/${s.id}`)}
                className="rc-btn"
                style={{ textAlign: 'left', padding: '10px 14px', width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{s.topic}</div>
                  <div className="rc-help">v{s.version} · {s.updated_at || s.created_at || ''}</div>
                </div>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--rc-muted)" strokeWidth="2" strokeLinecap="round">
                  <path d="M5 12h14M12 5l7 7-7 7"/>
                </svg>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

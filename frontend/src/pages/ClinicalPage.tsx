import { useMemo, useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
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
  const sheetsKey = ['clinical-sheets', projectId];

  // ── Projects query ────────────────────────────────────────────────────────
  const { data: projects = [] } = useQuery<Pick<Project, 'id' | 'title'>[]>({
    queryKey: ['projects-list'],
    queryFn: async () => {
      const r = await api.get('/projects');
      return (r.data as any[]).map(p => ({ id: p.id, title: p.title }));
    },
    staleTime: 60_000,
  });

  // ── Sheets query ──────────────────────────────────────────────────────────
  const { data: sheets = [], isLoading: sheetsLoading, error: sheetsError } = useQuery<ClinicalSheetRow[]>({
    queryKey: sheetsKey,
    queryFn: async () => {
      const params: any = {};
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
      }
    },
    onError: (e: any) => setGenError(e?.response?.data?.detail || 'Generate failed'),
  });

  // ── Job polling (React Query) ─────────────────────────────────────────────
  const navigatedRef = useRef(false);
  const { data: jobData } = useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const r = await api.get(`/jobs/${jobId}`);
      return r.data as { status: string; progress_percent: number; error?: string | null; result?: { sheet_id?: string } };
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === 'completed' || s === 'failed' ? false : 4000;
    },
  });

  useEffect(() => {
    if (!jobData) return;
    const { status, progress_percent, error, result } = jobData;
    setJobStatus({ status, progress: progress_percent, error: error ?? null, sheet_id: result?.sheet_id ?? null });
    if (status === 'completed') {
      qc.invalidateQueries({ queryKey: sheetsKey });
      setJobId(null);
      if (result?.sheet_id && !navigatedRef.current) {
        navigatedRef.current = true;
        navigate(`/clinical/sheets/${result.sheet_id}`);
      }
    }
    if (status === 'failed') setJobId(null);
  }, [jobData]);

  const errorMsg = genError || (sheetsError as any)?.message;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 980 }}>
      <div>
        <h1 className="rc-page-title">Clinical</h1>
        <div className="rc-subtitle">Generate an evidence-based clinical sheet (UpToDate-like), with traceable citations.</div>
      </div>

      {errorMsg && <div className="rc-error">{String(errorMsg)}</div>}

      {/* ── Project context banner ── */}
      {(fromProject || projectId) && (
        <div className="rc-card" style={{ background: 'rgba(79,70,229,0.06)', border: '1px solid rgba(79,70,229,0.15)' }}>
          <div style={{ fontSize: 13 }}>
            🔗 Usando papers del proyecto: <b>{projects.find(p => p.id === (fromProject || projectId))?.title || (fromProject || projectId)}</b>
            {' · '}
            <button className="rc-btn" style={{ padding: '2px 8px', fontSize: 12 }} onClick={() => setProjectId('')}>Quitar proyecto</button>
          </div>
          <button className="rc-btn" style={{ padding: '3px 10px', fontSize: 12 }} onClick={() => setProjectId('')}>
            Quitar proyecto
          </button>
        </div>
      )}

      {/* ── Generator form ── */}
      <div className="rc-card">
        <div className="rc-card-title">Topic</div>

        {/* Project selector — always visible, not hidden in advanced */}
        {projects.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div className="rc-kicker">Proyecto (opcional) — usa sus papers como evidencia</div>
            <select className="rc-select" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">(ninguno — solo fuentes online)</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>
        )}

        <textarea className="rc-textarea" value={topic} onChange={(e) => setTopic(e.target.value)}
          placeholder="Ej: Fractura por estrés del quinto metatarsiano" style={{ minHeight: 90 }} />

        <div style={{ height: 10 }} />
        <button className="rc-btn rc-btn--ghost" onClick={() => setAdvanced(v => !v)} style={{ fontSize: 12 }}>
          {advanced ? 'Hide advanced options' : 'Show advanced options'}
        </button>

        {advanced && (
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <div className="rc-kicker">Región/anatomía</div>
              <input className="rc-input" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Ej: pie/tobillo" />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div className="rc-kicker">Contexto clínico</div>
              <textarea className="rc-textarea" value={context} onChange={(e) => setContext(e.target.value)} placeholder="Edad, deporte, comorbilidades, escenario…" style={{ minHeight: 80 }} />
            </div>
            <div>
              <div className="rc-kicker">Objetivo</div>
              <select className="rc-select" value={objective} onChange={(e) => setObjective(e.target.value as any)}>
                <option value="clinical_decision">Decisión clínica</option>
                <option value="teaching">Docencia</option>
                <option value="presentation">Presentación</option>
                <option value="quick_review">Repaso rápido</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Nivel</div>
              <select className="rc-select" value={level} onChange={(e) => setLevel(e.target.value as any)}>
                <option value="R1">R1</option><option value="R3">R3</option>
                <option value="fellow">Fellow</option><option value="specialist">Especialista</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Enfoque</div>
              <select className="rc-select" value={focus} onChange={(e) => setFocus(e.target.value as any)}>
                <option value="complete">Completo</option><option value="diagnostic">Diagnóstico</option>
                <option value="conservative">Conservador</option><option value="surgical">Quirúrgico</option>
                <option value="rehab">Rehabilitación</option><option value="complications">Complicaciones</option>
              </select>
            </div>
            <div>
              <div className="rc-kicker">Extensión</div>
              <select className="rc-select" value={maxLength} onChange={(e) => setMaxLength(e.target.value as any)}>
                <option value="brief">Breve</option><option value="standard">Estándar</option><option value="exhaustive">Exhaustiva</option>
              </select>
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
              <input type="checkbox" checked={useProjectPapers} onChange={(e) => setUseProjectPapers(e.target.checked)} />
              Usar papers del proyecto
            </label>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
              <input type="checkbox" checked={searchOnline} onChange={(e) => setSearchOnline(e.target.checked)} />
              Buscar evidencia online
            </label>
          </div>
        )}

        <div style={{ height: 12 }} />
        <button className="rc-btn rc-btn--primary" disabled={!canGenerate || generateMut.isPending || Boolean(jobId)} onClick={() => generateMut.mutate()}>
          {jobId ? 'Running…' : generateMut.isPending ? 'Submitting…' : 'Consultar (tipo UpToDate)'}
        </button>
        {projectId && projectPaperCount && projectPaperCount > 0 && !jobId && !generateMut.isPending && (
          <div className="rc-help" style={{ marginTop: 6 }}>
            El pipeline usará {projectPaperCount} paper{projectPaperCount !== 1 ? 's' : ''} de tu proyecto + búsqueda online como evidencia.
          </div>
        )}

        {jobStatus && (
          <div style={{ marginTop: 12 }}>
            <div className="rc-help">
              status: <b>{jobStatus.status}</b> · {jobStatus.progress}%
              {jobStatus.error && <span className="rc-error"> · {String(jobStatus.error)}</span>}
            </div>
            <div style={{ height: 6 }} />
            <div className="rc-progress"><div style={{ width: `${Math.max(0, Math.min(100, jobStatus.progress))}%` }} /></div>
          </div>
        )}
      </div>

      {/* ── Sheets list ── */}
      <div className="rc-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div className="rc-card-title" style={{ marginBottom: 0 }}>Fichas recientes</div>
          <button className="rc-btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => qc.invalidateQueries({ queryKey: sheetsKey })} disabled={sheetsLoading}>
            {sheetsLoading ? '…' : '↻'}
          </button>
        </div>
        {sheets.length === 0 && !sheetsLoading
          ? <div className="rc-muted">No sheets yet. Generate your first one above.</div>
          : sheets.map(s => (
            <button key={s.id} onClick={() => navigate(`/clinical/sheets/${s.id}`)} className="rc-btn" style={{ textAlign: 'left', padding: 12, width: '100%', marginBottom: 8 }}>
              <div style={{ fontWeight: 850 }}>{s.topic}</div>
              <div className="rc-help">v{s.version} · {s.updated_at || s.created_at || ''}</div>
            </button>
          ))
        }
      </div>
    </div>
  );
}

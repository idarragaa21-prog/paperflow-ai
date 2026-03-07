import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';

type ProjectRow = { id: string; title: string };

type SheetRow = {
  id: string;
  project_id?: string | null;
  topic: string;
  version: number;
  created_at?: string | null;
  updated_at?: string | null;
};

export default function ClinicalPage() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectRow[]>([]);
  const [projectId, setProjectId] = useState<string>('');

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

  const [sheets, setSheets] = useState<SheetRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<{ status: string; progress: number; error?: string | null; sheet_id?: string | null } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canGenerate = useMemo(() => topic.trim().length > 0, [topic]);

  async function loadProjects() {
    try {
      const r = await api.get('/projects');
      setProjects((r.data as any[]).map((p) => ({ id: p.id, title: p.title })));
    } catch {
      // ignore
    }
  }

  async function loadSheets() {
    setLoading(true);
    setError(null);
    try {
      const params: any = {};
      if (projectId) params.project_id = projectId;
      const r = await api.get('/clinical/sheets', { params });
      setSheets(r.data as SheetRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load clinical sheets');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProjects();
    loadSheets();
  }, []);

  useEffect(() => {
    loadSheets();
  }, [projectId]);

  async function generate() {
    if (!canGenerate) return;
    setGenerating(true);
    setError(null);
    try {
      const payload: any = {
        topic: topic.trim(),
        project_id: projectId || null,
        context: context.trim() || null,
        objective,
        level,
        focus,
        region: region.trim() || null,
        max_length: maxLength,
        use_project_papers: useProjectPapers,
        search_online: searchOnline,
      };
      const r = await api.post('/clinical/query', payload);
      const jid = (r.data as any)?.job_id as string | undefined;
      if (jid) {
        setJobId(jid);
        setJobStatus({ status: 'queued', progress: 0, error: null, sheet_id: null });
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Generate failed');
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${jobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        const result = (r.data as any)?.result || {};
        const sheet_id = result?.sheet_id || null;
        setJobStatus({ status, progress, error: err, sheet_id });

        if (status === 'completed') {
          await loadSheets();
          setJobId(null);
          if (sheet_id) navigate(`/clinical/sheets/${sheet_id}`);
        }
        if (status === 'failed') {
          setJobId(null);
        }
      } catch (e: any) {
        setJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    poll();
    const t = window.setInterval(poll, 4000);
    return () => {
      stopped = true;
      window.clearInterval(t);
    };
  }, [jobId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 980 }}>
      <div>
        <h1 className="rc-page-title">Clinical</h1>
        <div className="rc-subtitle">Generate an evidence-based clinical sheet (UpToDate-like), with traceable citations.</div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={loadSheets} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Topic</div>
        <textarea className="rc-textarea" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Ej: Fractura por estrés del quinto metatarsiano" style={{ minHeight: 90 }} />

        <div style={{ height: 10 }} />

        <button className="rc-btn rc-btn--ghost" onClick={() => setAdvanced((v) => !v)} style={{ fontSize: 12 }}>
          {advanced ? 'Hide advanced options' : 'Show advanced options'}
        </button>

        {advanced ? (
          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Proyecto asociado (opcional)</div>
              <select className="rc-select" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">(none)</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Región/anatomía</div>
              <input className="rc-input" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Ej: pie/tobillo" />
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Contexto clínico</div>
              <textarea className="rc-textarea" value={context} onChange={(e) => setContext(e.target.value)} placeholder="Edad, deporte, comorbilidades, escenario…" style={{ minHeight: 80 }} />
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Objetivo</div>
              <select className="rc-select" value={objective} onChange={(e) => setObjective(e.target.value as any)}>
                <option value="clinical_decision">Decisión clínica</option>
                <option value="teaching">Docencia</option>
                <option value="presentation">Presentación</option>
                <option value="quick_review">Repaso rápido</option>
              </select>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Nivel</div>
              <select className="rc-select" value={level} onChange={(e) => setLevel(e.target.value as any)}>
                <option value="R1">R1</option>
                <option value="R3">R3</option>
                <option value="fellow">Fellow</option>
                <option value="specialist">Especialista</option>
              </select>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Enfoque</div>
              <select className="rc-select" value={focus} onChange={(e) => setFocus(e.target.value as any)}>
                <option value="complete">Completo</option>
                <option value="diagnostic">Diagnóstico</option>
                <option value="conservative">Conservador</option>
                <option value="surgical">Quirúrgico</option>
                <option value="rehab">Rehabilitación</option>
                <option value="complications">Complicaciones</option>
              </select>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Extensión</div>
              <select className="rc-select" value={maxLength} onChange={(e) => setMaxLength(e.target.value as any)}>
                <option value="brief">Breve</option>
                <option value="standard">Estándar</option>
                <option value="exhaustive">Exhaustiva</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input type="checkbox" checked={useProjectPapers} onChange={(e) => setUseProjectPapers(e.target.checked)} />
              <span style={{ fontSize: 12 }}>Usar papers del proyecto</span>
            </div>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input type="checkbox" checked={searchOnline} onChange={(e) => setSearchOnline(e.target.checked)} />
              <span style={{ fontSize: 12 }}>Buscar evidencia online</span>
            </div>
          </div>
        ) : null}

        <div style={{ height: 12 }} />
        <div style={{ height: 12 }} />
        <button className="rc-btn rc-btn--primary" disabled={!canGenerate || generating || Boolean(jobId)} onClick={generate}>
          {jobId ? 'Running…' : generating ? 'Submitting…' : 'Consultar (tipo UpToDate)'}
        </button>

        {jobStatus ? (
          <div style={{ marginTop: 12 }}>
            <div className="rc-help">
              status: {jobStatus.status} · {jobStatus.progress}%
              {jobStatus.error ? <span className="rc-error"> · {String(jobStatus.error)}</span> : null}
            </div>
            <div style={{ height: 6 }} />
            <div className="rc-progress">
              <div style={{ width: `${Math.max(0, Math.min(100, jobStatus.progress))}%` }} />
            </div>
          </div>
        ) : null}
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Fichas recientes</div>
        {sheets.length === 0 ? <div className="rc-muted">No sheets yet.</div> : null}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sheets.map((s) => (
            <button
              key={s.id}
              onClick={() => navigate(`/clinical/sheets/${s.id}`)}
              className="rc-btn"
              style={{ textAlign: 'left', padding: 12 }}
            >
              <div style={{ fontWeight: 850 }}>{s.topic}</div>
              <div className="rc-help">v{s.version} · {s.updated_at || s.created_at || ''}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

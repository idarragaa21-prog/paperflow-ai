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
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Clinical</div>
          <h2>Genera fichas clínicas con evidencia rastreable</h2>
          <p>
            Usa el mismo lenguaje visual del resto del producto para convertir una pregunta clínica en una ficha tipo UpToDate.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{sheets.length} fichas</span>
          {jobStatus ? <span className="rc-discover-badge">{jobStatus.status} · {jobStatus.progress}%</span> : null}
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-product-two-column rc-product-two-column--wide">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Prompt clínico</div>
              <div className="rc-help">Define tema, contexto y alcance. Las opciones avanzadas siguen disponibles cuando las necesites.</div>
            </div>
            <button className="rc-btn rc-btn--subtle" onClick={loadSheets} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>
          <textarea
            className="rc-discover-composer__input rc-product-textarea"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Ej: Fractura por estrés del quinto metatarsiano"
          />

          <button className="rc-btn rc-btn--subtle" onClick={() => setAdvanced((v) => !v)} style={{ fontSize: 12 }}>
          {advanced ? 'Hide advanced options' : 'Show advanced options'}
          </button>

          {advanced ? (
            <div className="rc-product-form-grid rc-product-form-grid--three" style={{ marginTop: 12 }}>
            <label className="rc-discover-filter-field">
              <span>Proyecto asociado (opcional)</span>
              <select className="rc-input" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">(none)</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </label>

            <label className="rc-discover-filter-field">
              <span>Región/anatomía</span>
              <input className="rc-input" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Ej: pie/tobillo" />
            </label>

            <label className="rc-discover-filter-field" style={{ gridColumn: '1 / -1' }}>
              <span>Contexto clínico</span>
              <textarea className="rc-discover-composer__input rc-product-textarea" value={context} onChange={(e) => setContext(e.target.value)} placeholder="Edad, deporte, comorbilidades, escenario…" />
            </label>

            <label className="rc-discover-filter-field">
              <span>Objetivo</span>
              <select className="rc-input" value={objective} onChange={(e) => setObjective(e.target.value as any)}>
                <option value="clinical_decision">Decisión clínica</option>
                <option value="teaching">Docencia</option>
                <option value="presentation">Presentación</option>
                <option value="quick_review">Repaso rápido</option>
              </select>
            </label>

            <label className="rc-discover-filter-field">
              <span>Nivel</span>
              <select className="rc-input" value={level} onChange={(e) => setLevel(e.target.value as any)}>
                <option value="R1">R1</option>
                <option value="R3">R3</option>
                <option value="fellow">Fellow</option>
                <option value="specialist">Especialista</option>
              </select>
            </label>

            <label className="rc-discover-filter-field">
              <span>Enfoque</span>
              <select className="rc-input" value={focus} onChange={(e) => setFocus(e.target.value as any)}>
                <option value="complete">Completo</option>
                <option value="diagnostic">Diagnóstico</option>
                <option value="conservative">Conservador</option>
                <option value="surgical">Quirúrgico</option>
                <option value="rehab">Rehabilitación</option>
                <option value="complications">Complicaciones</option>
              </select>
            </label>

            <label className="rc-discover-filter-field">
              <span>Extensión</span>
              <select className="rc-input" value={maxLength} onChange={(e) => setMaxLength(e.target.value as any)}>
                <option value="brief">Breve</option>
                <option value="standard">Estándar</option>
                <option value="exhaustive">Exhaustiva</option>
              </select>
            </label>

            <label className="rc-discover-toggle">
              <input type="checkbox" checked={useProjectPapers} onChange={(e) => setUseProjectPapers(e.target.checked)} />
              <span>Usar papers del proyecto</span>
            </label>

            <label className="rc-discover-toggle">
              <input type="checkbox" checked={searchOnline} onChange={(e) => setSearchOnline(e.target.checked)} />
              <span>Buscar evidencia online</span>
            </label>
          </div>
        ) : null}

          <div className="rc-product-actions">
            <button className="rc-btn rc-btn--primary" disabled={!canGenerate || generating || Boolean(jobId)} onClick={generate}>
          {jobId ? 'Running…' : generating ? 'Submitting…' : 'Consultar (tipo UpToDate)'}
            </button>
          </div>

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
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div className="rc-card-title">Fichas recientes</div>
          </div>
          {sheets.length === 0 ? <div className="rc-empty-state">No sheets yet.</div> : null}
          <div className="rc-product-record-list">
            {sheets.map((s) => (
              <button
                key={s.id}
                onClick={() => navigate(`/clinical/sheets/${s.id}`)}
                className="rc-list-button"
              >
                <div style={{ fontWeight: 850 }}>{s.topic}</div>
                <div className="rc-help">v{s.version} · {s.updated_at || s.created_at || ''}</div>
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

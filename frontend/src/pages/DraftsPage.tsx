import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../services/api';

type Draft = {
  id: string;
  title: string;
  status: string;
  version: number;
  sections: Array<{
    id: string;
    heading: string;
    content: string;
    citations: Array<{ id: string; marker: string }>;
  }>;
};

type EvidenceTable = {
  id: string;
  title: string;
  table_json: { count?: number };
  confidence: number;
};

export default function DraftsPage() {
  const { projectId } = useParams();
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [tables, setTables] = useState<EvidenceTable[]>([]);
  const [title, setTitle] = useState('Sintesis narrativa');
  const [heading, setHeading] = useState('Introduccion');
  const [selectedDraft, setSelectedDraft] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!projectId) return;
    const [draftResponse, evidenceResponse] = await Promise.all([
      api.get('/drafts', { params: { project_id: projectId } }),
      api.get('/evidence/tables', { params: { project_id: projectId } }),
    ]);
    const nextDrafts = draftResponse.data as Draft[];
    setDrafts(nextDrafts);
    setTables(evidenceResponse.data as EvidenceTable[]);
    if (!selectedDraft && nextDrafts[0]) {
      setSelectedDraft(nextDrafts[0].id);
    }
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'No se pudieron cargar los borradores'));
  }, [projectId]);

  async function createDraft() {
    if (!projectId || !title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.post('/drafts', { project_id: projectId, title });
      const draft = response.data as Draft;
      setSelectedDraft(draft.id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el borrador');
    } finally {
      setBusy(false);
    }
  }

  async function generateSection() {
    if (!selectedDraft || !heading.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/drafts/${selectedDraft}/generate-section`, { heading, paper_ids: [], extraction_record_ids: [] });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo generar la seccion');
    } finally {
      setBusy(false);
    }
  }

  async function buildEvidence() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      await api.get('/evidence/tables', { params: { project_id: projectId, build: true } });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo construir la tabla de evidencia');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--teal">Paso 4 · Redactar</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Convierte la evidencia en un borrador</h1>
          <div className="rc-subtitle">Crea espacios de escritura, genera secciones con evidencia y mantén las citas unidas al texto desde el inicio.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>La redaccion debe sentirse como una continuacion de la extraccion, no como una herramienta aparte. Construye tablas de evidencia y luego conviertelas en secciones.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{drafts.length}</strong><span>Borradores</span></div>
          <div className="rc-metric-tile"><strong>{tables.length}</strong><span>Tablas de evidencia</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Borradores</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">Titulo del nuevo borrador</div>
              <input data-testid="draft-title-input" className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <button data-testid="draft-create-button" className="rc-btn rc-btn--primary" onClick={createDraft} disabled={busy}>Crear borrador</button>
            <button data-testid="draft-build-evidence" className="rc-btn" onClick={buildEvidence} disabled={busy}>Construir tabla de evidencia</button>
          </div>
          <div className="rc-help" style={{ marginTop: 10 }}>Empieza con un titulo de trabajo y luego genera una seccion a la vez a partir de la evidencia que ya extrajiste.</div>
        </div>

        <div className="rc-next-step">
          <div className="rc-kicker">Siguiente paso sugerido</div>
          <div style={{ fontWeight: 800, letterSpacing: '-0.02em', marginTop: 4 }}>Construye una seccion desde la evidencia</div>
          <div className="rc-help" style={{ marginTop: 8 }}>Elige un borrador, genera una seccion con evidencia y luego pasa a Analisis cuando necesites salidas formales y reportes reproducibles.</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">Borrador</div>
              <select data-testid="draft-select" className="rc-input" value={selectedDraft} onChange={(e) => setSelectedDraft(e.target.value)}>
                <option value="">Seleccionar borrador</option>
                {drafts.map((draft) => (
                  <option key={draft.id} value={draft.id}>
                    {draft.title} · v{draft.version}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">Encabezado</div>
              <input data-testid="draft-heading-input" className="rc-input" value={heading} onChange={(e) => setHeading(e.target.value)} />
            </div>
            <button data-testid="draft-generate-button" className="rc-btn" onClick={generateSection} disabled={busy || !selectedDraft}>Generar</button>
          </div>
          <div className="rc-row" style={{ marginTop: 12 }}>
            <Link className="rc-btn" to={`/projects/${projectId}/meta`}>Volver a extraccion</Link>
            <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/analysis`}>Continuar al analisis</Link>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Contenido del borrador</div>
          {drafts.length === 0 ? <div className="rc-muted">Todavia no hay borradores.</div> : null}
          {drafts.map((draft) => (
            <div key={draft.id} style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
              <div style={{ fontWeight: 800 }}>{draft.title} · {draft.status} · v{draft.version}</div>
              {draft.sections.map((section) => (
                <div key={section.id} className="rc-soft-card">
                  <div className="rc-kicker">{section.heading}</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{section.content}</div>
                  <div className="rc-help">Citas: {section.citations.map((citation) => citation.marker).join(', ') || 'ninguna'}</div>
                </div>
              ))}
            </div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Tablas de evidencia</div>
          {tables.length === 0 ? <div className="rc-muted">Todavia no hay tablas de evidencia.</div> : null}
          {tables.map((table) => (
            <div key={table.id} className="rc-soft-card" style={{ marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{table.title}</div>
              <div className="rc-help">Filas: {table.table_json?.count ?? 0} · confianza {table.confidence.toFixed(2)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

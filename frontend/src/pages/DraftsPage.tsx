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
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Paso 4 · Redactar</div>
          <h2>Convierte la evidencia en un borrador editable</h2>
          <p>
            Crea un espacio de escritura, genera secciones con evidencia y conserva las citas cerca del texto desde el
            inicio.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{drafts.length} borradores</span>
          <span className="rc-discover-badge">{tables.length} tablas de evidencia</span>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Crear borrador</div>
              <div className="rc-help">Empieza con un título de trabajo y construye una sección a la vez.</div>
            </div>
          </div>
          <div className="rc-product-form-grid">
            <label className="rc-discover-filter-field">
              <span>Título del nuevo borrador</span>
              <input data-testid="draft-title-input" className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
          </div>
          <div className="rc-product-actions">
            <button data-testid="draft-create-button" className="rc-btn rc-btn--primary" onClick={createDraft} disabled={busy}>
              Crear borrador
            </button>
            <button data-testid="draft-build-evidence" className="rc-btn rc-btn--subtle" onClick={buildEvidence} disabled={busy}>
              Construir tabla de evidencia
            </button>
          </div>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Siguiente paso sugerido</div>
              <div className="rc-help">Genera una sección desde la evidencia y continúa a análisis cuando necesites salidas formales.</div>
            </div>
          </div>
          <div className="rc-product-form-grid">
            <label className="rc-discover-filter-field">
              <span>Borrador</span>
              <select data-testid="draft-select" className="rc-input" value={selectedDraft} onChange={(e) => setSelectedDraft(e.target.value)}>
                <option value="">Seleccionar borrador</option>
                {drafts.map((draft) => (
                  <option key={draft.id} value={draft.id}>
                    {draft.title} · v{draft.version}
                  </option>
                ))}
              </select>
            </label>
            <label className="rc-discover-filter-field">
              <span>Encabezado</span>
              <input data-testid="draft-heading-input" className="rc-input" value={heading} onChange={(e) => setHeading(e.target.value)} />
            </label>
          </div>
          <div className="rc-product-actions">
            <button data-testid="draft-generate-button" className="rc-btn rc-btn--primary" onClick={generateSection} disabled={busy || !selectedDraft}>
              Generar sección
            </button>
            <Link className="rc-btn rc-btn--subtle" to={`/projects/${projectId}/meta`}>Volver a extracción</Link>
            <Link className="rc-btn rc-btn--subtle" to={`/projects/${projectId}/analysis`}>Ir a análisis</Link>
          </div>
        </section>
      </div>

      <div className="rc-product-two-column rc-product-two-column--wide">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div className="rc-card-title">Contenido del borrador</div>
          </div>
          {drafts.length === 0 ? <div className="rc-muted">Todavia no hay borradores.</div> : null}
          <div className="rc-product-record-list">
            {drafts.map((draft) => (
            <div key={draft.id} className="rc-product-record rc-product-record--soft">
              <div style={{ fontWeight: 800 }}>{draft.title} · {draft.status} · v{draft.version}</div>
              {draft.sections.map((section) => (
                <div key={section.id} className="rc-product-study-panel" style={{ marginTop: 10 }}>
                  <div className="rc-kicker">{section.heading}</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{section.content}</div>
                  <div className="rc-help">Citas: {section.citations.map((citation) => citation.marker).join(', ') || 'ninguna'}</div>
                </div>
              ))}
            </div>
          ))}
          </div>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div className="rc-card-title">Tablas de evidencia</div>
          </div>
          {tables.length === 0 ? <div className="rc-muted">Todavia no hay tablas de evidencia.</div> : null}
          <div className="rc-product-record-list">
            {tables.map((table) => (
            <div key={table.id} className="rc-product-study-panel">
              <div style={{ fontWeight: 800 }}>{table.title}</div>
              <div className="rc-help">Filas: {table.table_json?.count ?? 0} · confianza {table.confidence.toFixed(2)}</div>
            </div>
          ))}
          </div>
        </section>
      </div>
    </div>
  );
}

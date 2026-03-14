import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type ReferenceRow = {
  id: string;
  title: string;
  authors: string[];
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  source_format: string;
};

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

export default function ReferencesPage() {
  const { projectId } = useParams();
  const [items, setItems] = useState<ReferenceRow[]>([]);
  const [format, setFormat] = useState<'bibtex' | 'ris'>('bibtex');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState<number | undefined>(undefined);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load(cursor?: string | null, append = false) {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/references', {
        params: { project_id: projectId, limit: 50, cursor: cursor || undefined },
      });
      const page = r.data as PaginatedResponse<ReferenceRow>;
      setItems((prev) => (append ? [...prev, ...page.items] : page.items));
      setNextCursor(page.next_cursor || null);
      setHasMore(Boolean(page.has_more));
      setTotalCount(page.total_count);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar las referencias');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [projectId]);

  const canImport = useMemo(() => Boolean(projectId && content.trim()), [projectId, content]);
  const doiCount = useMemo(() => items.filter((item) => Boolean(item.doi)).length, [items]);
  const formatsPresent = useMemo(() => new Set(items.map((item) => item.source_format.toUpperCase())).size, [items]);

  async function syncFromLibrary() {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      const r = await api.post('/references/sync-from-library', null, { params: { project_id: projectId } });
      setNotice(`Referencias creadas desde la biblioteca: ${String(r.data?.created || 0)}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La sincronizacion con la biblioteca fallo');
    }
  }

  async function importReferences() {
    if (!projectId || !content.trim()) return;
    setImporting(true);
    setError(null);
    setNotice(null);
    try {
      const r = await api.post('/references/import', {
        project_id: projectId,
        format,
        content,
      });
      setNotice(`Importadas ${String(r.data?.imported || 0)} referencias, se omitieron ${String(r.data?.skipped || 0)} duplicados.`);
      setContent('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La importacion fallo');
    } finally {
      setImporting(false);
    }
  }

  async function exportReferences(nextFormat: 'bibtex' | 'ris') {
    if (!projectId) return;
    setError(null);
    try {
      const r = await api.get('/references/export', {
        params: { project_id: projectId, format: nextFormat },
        responseType: 'blob',
      });
      const blob = r.data as Blob;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `references.${nextFormat === 'bibtex' ? 'bib' : 'ris'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La exportacion fallo');
    }
  }

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Referencias</div>
          <h2>Bibliografía limpia y exportable</h2>
          <p>
            Sincroniza desde la biblioteca, importa BibTeX o RIS y mantén una referencia consistente para escritura y
            revisión.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{totalCount ?? items.length} referencias</span>
          <span className="rc-discover-badge">{doiCount} con DOI</span>
          <span className="rc-discover-badge">{formatsPresent || '—'} formatos</span>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-soft-card"><div className="rc-help">{notice}</div></div> : null}

      <div className="rc-product-two-column rc-product-two-column--wide">
        <div className="rc-product-stack">
          <section className="rc-product-card">
            <div className="rc-product-card__header">
              <div className="rc-card-title">Operaciones de referencias</div>
            </div>
            <div className="rc-help" style={{ marginBottom: 12 }}>Mantiene la bibliografia del proyecto alineada con tu biblioteca y exporta citas para escritura o herramientas de revision.</div>
            <div className="rc-card-list">
              <button className="rc-btn rc-btn--primary" onClick={syncFromLibrary}>Sincronizar desde biblioteca</button>
              <button className="rc-btn" onClick={() => exportReferences('bibtex')}>Exportar BibTeX</button>
              <button className="rc-btn" onClick={() => exportReferences('ris')}>Exportar RIS</button>
              <button className="rc-btn rc-btn--ghost" onClick={() => { void load(); }} disabled={loading}>
                {loading ? 'Actualizando...' : 'Actualizar catalogo'}
              </button>
            </div>
          </section>

          <section className="rc-product-card">
            <div className="rc-product-card__header">
              <div className="rc-card-title">Importar referencias</div>
            </div>
            <div className="rc-product-form-grid">
              <label className="rc-discover-filter-field" style={{ maxWidth: 160 }}>
                <span>Formato</span>
                <select
                  data-testid="references-format-select"
                  className="rc-input"
                  value={format}
                  onChange={(e) => setFormat(e.target.value as 'bibtex' | 'ris')}
                >
                  <option value="bibtex">BibTeX</option>
                  <option value="ris">RIS</option>
                </select>
              </label>
              <button
                data-testid="references-import-button"
                className="rc-btn rc-btn--primary"
                disabled={!canImport || importing}
                onClick={importReferences}
              >
                {importing ? 'Importando...' : `Importar ${format.toUpperCase()}`}
              </button>
            </div>
            <div className="rc-help" style={{ marginTop: 8 }}>Pega citas, papers de congresos o exportaciones de revistas. Los duplicados se ignoran durante la importacion.</div>
            <textarea
              data-testid="references-content-input"
              className="rc-discover-composer__input rc-product-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={format === 'bibtex' ? '@article{...}' : 'TY  - JOUR'}
            />
          </section>
        </div>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 4 }}>Bibliografia del proyecto</div>
              <div className="rc-help">Lista desplazable y deduplicada de referencias para el proyecto actual.</div>
            </div>
            {hasMore ? (
              <button className="rc-btn rc-btn--subtle" onClick={() => void load(nextCursor, true)} disabled={loading}>
                {loading ? 'Cargando...' : 'Cargar mas'}
              </button>
            ) : null}
          </div>

          {loading && items.length === 0 ? (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Cargando referencias</div>
              <div className="rc-help">Trayendo la primera pagina de citas para este proyecto.</div>
            </div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay referencias</div>
              <div className="rc-help">Importa un archivo BibTeX o RIS, o sincroniza la bibliografia desde la biblioteca para empezar a escribir con citas.</div>
            </div>
          ) : null}

          <div className="rc-card-list">
            {items.map((item) => (
              <div key={item.id} className="rc-soft-card">
                <div className="rc-detail-header">
                  <div style={{ flex: 1, minWidth: 220 }}>
                    <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{item.title}</div>
                    <div className="rc-help" style={{ marginTop: 8 }}>
                      {item.authors.join(', ') || 'Autores desconocidos'}
                      {item.journal ? ` · ${item.journal}` : ''}
                      {item.publication_year ? ` · ${item.publication_year}` : ''}
                    </div>
                  </div>
                  <span className="rc-badge">{item.source_format.toUpperCase()}</span>
                </div>
                <div className="rc-row" style={{ marginTop: 10 }}>
                  {item.doi ? <span className="rc-badge rc-badge--success">DOI {item.doi}</span> : null}
                  {item.pmid ? <span className="rc-badge">PMID {item.pmid}</span> : null}
                  {!item.doi && !item.pmid ? <span className="rc-badge">Solo metadatos</span> : null}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

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
      setError(e?.response?.data?.detail || 'Failed to load references');
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
      setNotice(`References created from library: ${String(r.data?.created || 0)}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Library sync failed');
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
      setNotice(`Imported ${String(r.data?.imported || 0)} references, skipped ${String(r.data?.skipped || 0)} duplicates.`);
      setContent('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Import failed');
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
      setError(e?.response?.data?.detail || 'Export failed');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">References</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>References</h1>
          <div className="rc-subtitle">Build a clean project bibliography, sync from the library and move between BibTeX or RIS without leaving the workspace.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{totalCount ?? items.length}</strong><span>References</span></div>
          <div className="rc-metric-tile"><strong>{doiCount}</strong><span>With DOI</span></div>
          <div className="rc-metric-tile"><strong>{formatsPresent || '—'}</strong><span>Formats in catalog</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-soft-card"><div className="rc-help">{notice}</div></div> : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-stack">
          <div className="rc-card">
            <div className="rc-card-title">Reference operations</div>
            <div className="rc-help" style={{ marginBottom: 12 }}>Keep the project bibliography aligned with your paper library and export citations for writing or review tools.</div>
            <div className="rc-card-list">
              <button className="rc-btn rc-btn--primary" onClick={syncFromLibrary}>Sync from Library</button>
              <button className="rc-btn" onClick={() => exportReferences('bibtex')}>Export BibTeX</button>
              <button className="rc-btn" onClick={() => exportReferences('ris')}>Export RIS</button>
              <button className="rc-btn rc-btn--ghost" onClick={() => { void load(); }} disabled={loading}>
                {loading ? 'Refreshing...' : 'Refresh catalog'}
              </button>
            </div>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">Import references</div>
            <div className="rc-row" style={{ alignItems: 'flex-end' }}>
              <div style={{ width: 160 }}>
                <div className="rc-kicker">Format</div>
                <select
                  data-testid="references-format-select"
                  className="rc-input"
                  value={format}
                  onChange={(e) => setFormat(e.target.value as 'bibtex' | 'ris')}
                >
                  <option value="bibtex">BibTeX</option>
                  <option value="ris">RIS</option>
                </select>
              </div>
              <button
                data-testid="references-import-button"
                className="rc-btn rc-btn--primary"
                disabled={!canImport || importing}
                onClick={importReferences}
              >
                {importing ? 'Importing...' : `Import ${format.toUpperCase()}`}
              </button>
            </div>
            <div className="rc-help" style={{ marginTop: 8 }}>Paste citations, conference papers or journal exports. Duplicates are ignored during import.</div>
            <div style={{ height: 12 }} />
            <textarea
              data-testid="references-content-input"
              className="rc-input"
              style={{ minHeight: 240, width: '100%' }}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={format === 'bibtex' ? '@article{...}' : 'TY  - JOUR'}
            />
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-toolbar">
            <div>
              <div className="rc-card-title" style={{ marginBottom: 4 }}>Project bibliography</div>
              <div className="rc-help">Scrollable, deduplicated reference list for the current project.</div>
            </div>
            {hasMore ? (
              <button className="rc-btn" onClick={() => void load(nextCursor, true)} disabled={loading}>
                {loading ? 'Loading...' : 'Load more'}
              </button>
            ) : null}
          </div>
          <div style={{ height: 12 }} />

          {loading && items.length === 0 ? (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>Loading references</div>
              <div className="rc-help">Pulling the first page of citations for this project.</div>
            </div>
          ) : null}

          {!loading && items.length === 0 ? (
            <div className="rc-empty-state">
              <div style={{ fontWeight: 800, marginBottom: 6 }}>No references yet</div>
              <div className="rc-help">Import a BibTeX or RIS file, or sync the bibliography from the paper library to start writing with citations.</div>
            </div>
          ) : null}

          <div className="rc-card-list">
            {items.map((item) => (
              <div key={item.id} className="rc-soft-card">
                <div className="rc-detail-header">
                  <div style={{ flex: 1, minWidth: 220 }}>
                    <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{item.title}</div>
                    <div className="rc-help" style={{ marginTop: 8 }}>
                      {item.authors.join(', ') || 'Unknown authors'}
                      {item.journal ? ` · ${item.journal}` : ''}
                      {item.publication_year ? ` · ${item.publication_year}` : ''}
                    </div>
                  </div>
                  <span className="rc-badge">{item.source_format.toUpperCase()}</span>
                </div>
                <div className="rc-row" style={{ marginTop: 10 }}>
                  {item.doi ? <span className="rc-badge rc-badge--success">DOI {item.doi}</span> : null}
                  {item.pmid ? <span className="rc-badge">PMID {item.pmid}</span> : null}
                  {!item.doi && !item.pmid ? <span className="rc-badge">Metadata only</span> : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

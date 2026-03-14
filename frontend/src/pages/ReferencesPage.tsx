import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';

type ReferenceRow = {
  id: string;
  paper_id?: string | null;
  title: string;
  authors: string[];
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  pmcid?: string | null;
  source_format: string;
  citation_key?: string | null;
  language?: string | null;
};

function buildAPA(r: ReferenceRow): string {
  const authorsStr = r.authors.length > 0 ? r.authors.join(', ') : 'Unknown';
  const year = r.publication_year ? `(${r.publication_year})` : '(n.d.)';
  const title = r.title || 'Untitled';
  const journal = r.journal ? `${r.journal}` : '';
  return `${authorsStr} ${year}. ${title}. ${journal}.`.replace(/\.\./g, '.').trim();
}

function buildBibTeX(r: ReferenceRow): string {
  const key = r.citation_key || r.doi || r.pmid || r.id.split('-')[0];
  const authors = r.authors.length > 0 ? r.authors.join(' and ') : '';
  const lines = [`@article{${key}`];
  if (authors) lines.push(`  author = {${authors}}`);
  if (r.title) lines.push(`  title = {${r.title}}`);
  if (r.journal) lines.push(`  journal = {${r.journal}}`);
  if (r.publication_year) lines.push(`  year = {${r.publication_year}}`);
  if (r.doi) lines.push(`  doi = {${r.doi}}`);
  return lines.join(',\n') + '\n}';
}

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  window.URL.revokeObjectURL(url);
}

function truncate(s: string, max: number) {
  return s.length > max ? s.slice(0, max) + '\u2026' : s;
}

export default function ReferencesPage() {
  const { projectId } = useParams();
  const toast = useToast();

  const [items, setItems] = useState<ReferenceRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Import section
  const [format, setFormat] = useState<'bibtex' | 'ris'>('bibtex');
  const [content, setContent] = useState('');
  const [importing, setImporting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // DOI import
  const [doiInput, setDoiInput] = useState('');
  const [doiLoading, setDoiLoading] = useState(false);

  async function load() {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const r = await api.get('/references', { params: { project_id: projectId } });
      setItems(r.data as ReferenceRow[]);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error cargando referencias'); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [projectId]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return items;
    return items.filter(r =>
      r.title.toLowerCase().includes(q) ||
      r.authors.some(a => a.toLowerCase().includes(q)) ||
      (r.journal || '').toLowerCase().includes(q)
    );
  }, [items, search]);

  function copyAPA(r: ReferenceRow) {
    navigator.clipboard.writeText(buildAPA(r));
    toast.success('\u2713 Copied', 'APA citation copied to clipboard.');
  }

  function downloadBib(r: ReferenceRow) {
    const bib = buildBibTeX(r);
    const key = r.citation_key || r.id.split('-')[0];
    downloadText(bib, `${key}.bib`);
  }

  function exportAllBibTeX() {
    if (items.length === 0) { toast.info('No references', 'Nothing to export.'); return; }
    const all = items.map(r => buildBibTeX(r)).join('\n\n');
    downloadText(all, 'references.bib');
    toast.success('Exported', `${items.length} references as BibTeX.`);
  }

  async function syncFromLibrary() {
    if (!projectId) return;
    setError(null); setNotice(null);
    try {
      const r = await api.post('/references/sync-from-library', null, { params: { project_id: projectId } });
      setNotice(`Referencias creadas desde library: ${String((r.data as any)?.created || 0)}`);
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Sync fallido'); }
  }

  async function importReferences() {
    if (!projectId || !content.trim()) return;
    setImporting(true); setError(null); setNotice(null);
    try {
      const r = await api.post('/references/import', { project_id: projectId, format, content });
      setNotice(`Importados: ${(r.data as any)?.imported || 0}, duplicados: ${(r.data as any)?.skipped || 0}.`);
      setContent('');
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Import fallido'); }
    finally { setImporting(false); }
  }

  async function importByDOI() {
    if (!projectId || !doiInput.trim()) return;
    setDoiLoading(true); setError(null);
    try {
      // Try to download the paper, which resolves metadata
      await api.post('/papers/download', { project_id: projectId, doi: doiInput.trim() });
      // Then sync references from library to pick it up
      await api.post('/references/sync-from-library', null, { params: { project_id: projectId } });
      toast.success('DOI imported', `Paper downloaded and added to references.`);
      setDoiInput('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'DOI import failed. Paper may not be open access.');
    } finally { setDoiLoading(false); }
  }

  async function exportServer(fmt: 'bibtex' | 'ris') {
    if (!projectId) return;
    setError(null);
    try {
      const r = await api.get('/references/export', { params: { project_id: projectId, format: fmt }, responseType: 'blob' });
      const blob = r.data as Blob;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `references.${fmt === 'bibtex' ? 'bib' : 'ris'}`;
      document.body.appendChild(a); a.click(); a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Export failed'); }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">References</h1>
        <div className="rc-subtitle">Import BibTeX or RIS, sync items from the project library and export clean citations.</div>
      </div>

      <div className="rc-row" style={{ flexWrap: 'wrap' }}>
        <button className="rc-btn" onClick={load} disabled={loading}>{loading ? 'Loading...' : 'Refresh'}</button>
        <button className="rc-btn" onClick={syncFromLibrary}>Sync from Library</button>
        <button className="rc-btn rc-btn--primary" onClick={exportAllBibTeX}>Export all as BibTeX</button>
        <button className="rc-btn" onClick={() => exportServer('ris')}>Export RIS</button>
      </div>

      {error && <div className="rc-error">{error}</div>}
      {notice && <div className="rc-help" style={{ background: 'rgba(22,163,74,0.08)', padding: '8px 12px', borderRadius: 10 }}>{notice}</div>}

      {/* DOI import */}
      <div className="rc-card" style={{ padding: '10px 14px' }}>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <div className="rc-kicker">Import by DOI</div>
            <input className="rc-input" value={doiInput} onChange={e => setDoiInput(e.target.value)} placeholder="10.1000/xyz123" style={{ fontSize: 13 }} />
          </div>
          <button className="rc-btn rc-btn--primary" disabled={!doiInput.trim() || doiLoading} onClick={importByDOI} style={{ padding: '8px 14px', fontSize: 13 }}>
            {doiLoading ? 'Importing...' : 'Import DOI'}
          </button>
        </div>
      </div>

      {/* Import BibTeX/RIS colapsable */}
      <div className="rc-card" style={{ padding: importOpen ? 14 : '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setImportOpen(!importOpen)}>
          <span style={{ fontWeight: 800, fontSize: 13 }}>Import BibTeX / RIS</span>
          <span style={{ fontSize: 11, opacity: 0.6 }}>{importOpen ? '\u25B2' : '\u25BC'}</span>
        </div>
        {importOpen && (
          <div style={{ marginTop: 10 }}>
            <div className="rc-row" style={{ alignItems: 'flex-end', marginBottom: 8 }}>
              <div style={{ width: 140 }}>
                <div className="rc-kicker">Format</div>
                <select className="rc-input" value={format} onChange={e => setFormat(e.target.value as 'bibtex' | 'ris')}>
                  <option value="bibtex">BibTeX</option>
                  <option value="ris">RIS</option>
                </select>
              </div>
              <button className="rc-btn rc-btn--primary" disabled={!content.trim() || importing} onClick={importReferences}>
                {importing ? 'Importing...' : 'Import'}
              </button>
            </div>
            <textarea className="rc-input" style={{ minHeight: 140, width: '100%' }} value={content} onChange={e => setContent(e.target.value)} placeholder={format === 'bibtex' ? '@article{...}' : 'TY  - JOUR'} />
          </div>
        )}
      </div>

      {/* Search */}
      <input className="rc-input" style={{ maxWidth: 320, padding: '8px 12px', fontSize: 13 }} placeholder="Buscar titulo, autores o journal..." value={search} onChange={e => setSearch(e.target.value)} />

      {/* Tabla */}
      {items.length === 0 && !loading ? (
        <div className="rc-card" style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>{'\uD83D\uDCDA'}</div>
          <div style={{ fontWeight: 800, marginBottom: 4 }}>No references yet</div>
          <div className="rc-help">Sync from Library, import BibTeX/RIS, or add by DOI.</div>
        </div>
      ) : null}

      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--rc-border)', textAlign: 'left' }}>
                <th style={{ padding: '8px 6px' }}>Citation</th>
                <th style={{ padding: '8px 6px', width: 80 }}>Type</th>
                <th style={{ padding: '8px 6px', width: 80 }}>Paper</th>
                <th style={{ padding: '8px 6px', width: 160 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid var(--rc-border)' }}>
                  <td style={{ padding: '8px 6px', lineHeight: 1.4 }}>
                    <span style={{ fontWeight: 600 }}>{r.authors.length > 0 ? truncate(r.authors.join(', '), 50) : 'Unknown'}</span>
                    {r.publication_year ? ` (${r.publication_year})` : ''}.{' '}
                    <span title={r.title}>{truncate(r.title, 60)}</span>.{' '}
                    {r.journal && <em>{r.journal}</em>}.
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    {r.source_format ? <span className="rc-badge" style={{ fontSize: 11 }}>{r.source_format}</span> : '\u2014'}
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    {r.paper_id ? (
                      <Link to={`/projects/${projectId}/library`} style={{ fontSize: 11 }}>View</Link>
                    ) : <span className="rc-help">{'\u2014'}</span>}
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    <div className="rc-row" style={{ gap: 4 }}>
                      <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => copyAPA(r)}>Copy APA</button>
                      <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => downloadBib(r)}>BibTeX</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

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

export default function ReferencesPage() {
  const { projectId } = useParams();
  const [items, setItems] = useState<ReferenceRow[]>([]);
  const [format, setFormat] = useState<'bibtex' | 'ris'>('bibtex');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/references', { params: { project_id: projectId } });
      setItems(r.data as ReferenceRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load references');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [projectId]);

  const canImport = useMemo(() => Boolean(projectId && content.trim()), [projectId, content]);

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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">References</h1>
        <div className="rc-subtitle">Import BibTeX or RIS, sync items from the project library and export clean citations.</div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={load} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
        <button className="rc-btn" onClick={syncFromLibrary}>Sync from Library</button>
        <button className="rc-btn" onClick={() => exportReferences('bibtex')}>Export BibTeX</button>
        <button className="rc-btn" onClick={() => exportReferences('ris')}>Export RIS</button>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Import references</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ width: 160 }}>
            <div className="rc-kicker">Format</div>
            <select className="rc-input" value={format} onChange={(e) => setFormat(e.target.value as 'bibtex' | 'ris')}>
              <option value="bibtex">BibTeX</option>
              <option value="ris">RIS</option>
            </select>
          </div>
          <button className="rc-btn rc-btn--primary" disabled={!canImport || importing} onClick={importReferences}>
            {importing ? 'Importing…' : 'Import'}
          </button>
        </div>
        <div style={{ height: 10 }} />
        <textarea
          className="rc-input"
          style={{ minHeight: 220, width: '100%' }}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={format === 'bibtex' ? '@article{...}' : 'TY  - JOUR'}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.length === 0 ? <div className="rc-muted">No references yet.</div> : null}
        {items.map((item) => (
          <div key={item.id} className="rc-card">
            <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{item.title}</div>
            <div className="rc-help">
              {item.authors.join(', ')}
              {item.journal ? ` · ${item.journal}` : ''}
              {item.publication_year ? ` · ${item.publication_year}` : ''}
              {item.doi ? ` · DOI: ${item.doi}` : ''}
              {item.pmid ? ` · PMID: ${item.pmid}` : ''}
              {item.source_format ? ` · ${item.source_format}` : ''}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type PaperRow = {
  id: string;
  title: string;
  authors?: string | null;
  journal?: string | null;
  publication_year?: number | null;
  doi?: string | null;
  pmid?: string | null;
  filename: string;
  file_size_kb?: number | null;
  is_processed: boolean;
  processing_status?: string;
  processing_warnings?: string[];
  source_provider?: string | null;
  source_type?: string | null;
  is_open_access?: boolean;
  favorite?: boolean;
  created_at?: string | null;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export default function PapersPage() {
  const { projectId } = useParams();

  const toast = useToast();
  const confirm = useConfirm();

  const [papers, setPapers] = useState<PaperRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [doi, setDoi] = useState('');
  const [pmid, setPmid] = useState('');
  const [downloading, setDownloading] = useState(false);

  const canDownload = useMemo(() => Boolean(projectId && (doi.trim() || pmid.trim())), [projectId, doi, pmid]);

  async function load() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const rp = await api.get(`/projects/${projectId}/library`);
      setPapers(rp.data as PaperRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load papers');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [projectId]);

  async function upload() {
    if (!projectId || !uploadFile) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      form.append('file', uploadFile);
      const r = await api.post('/papers/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const duplicate = Boolean((r.data as any)?.duplicate);
      toast.info(duplicate ? 'Duplicate' : 'Uploaded', duplicate ? 'Paper already exists in this project.' : 'PDF uploaded successfully.');
      setUploadFile(null);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  async function downloadOA() {
    if (!projectId) return;
    setDownloading(true);
    setError(null);
    try {
      const payload: any = {
        project_id: projectId,
      };
      if (doi.trim()) payload.doi = doi.trim();
      if (pmid.trim()) payload.pmid = pmid.trim();
      await api.post('/papers/download', payload);
      toast.success('Download requested', 'OA resolver job started (duplicates are deduped).');
      setDoi('');
      setPmid('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Download failed');
    } finally {
      setDownloading(false);
    }
  }

  async function downloadFile(p: PaperRow) {
    setError(null);
    try {
      const r = await api.get(`/papers/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'paper.pdf');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'File download failed');
    }
  }

  async function processPaper(p: PaperRow) {
    setError(null);
    try {
      const r = await api.post(`/papers/${p.id}/process`);
      toast.success('Job enqueued', `Process: ${String(r.data?.job_id || '')}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to enqueue process job');
    }
  }

  async function summarizePaper(p: PaperRow) {
    setError(null);
    try {
      const r = await api.post('/notes/summarize', {
        paper_id: p.id,
        custom_instructions: null,
      });
      toast.success('Job enqueued', `Summarize: ${String(r.data?.job_id || '')}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to enqueue summarize job');
    }
  }

  async function deletePaper(p: PaperRow) {
    const ok = await confirm({
      title: `Delete paper?`,
      body: `This will delete the stored PDF file.\n\n${p.title}`,
      confirmText: 'Delete',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.delete(`/papers/${p.id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Delete failed');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Library</h1>
        <div className="rc-subtitle">Curate PDFs, deduplicate sources, process full text and build a reusable project library.</div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Download OA (by DOI / PMID)</div>
        <div className="rc-row" style={{ alignItems: 'flex-end' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">DOI</div>
            <input className="rc-input" value={doi} onChange={(e) => setDoi(e.target.value)} placeholder="10.xxxx/xxxxx" />
          </div>
          <div style={{ width: 180 }}>
            <div className="rc-kicker">PMID</div>
            <input className="rc-input" value={pmid} onChange={(e) => setPmid(e.target.value)} placeholder="12345678" />
          </div>
          <button className="rc-btn rc-btn--primary" disabled={!canDownload || downloading} onClick={downloadOA}>
            {downloading ? 'Downloading…' : 'Download'}
          </button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Upload PDF</div>
        <div className="rc-row" style={{ alignItems: 'center' }}>
          <input type="file" accept="application/pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
          <button className="rc-btn rc-btn--primary" disabled={!uploadFile || uploading} onClick={upload}>
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
        <div className="rc-help" style={{ marginTop: 8 }}>Uploads are deduplicated server-side (hash + metadata).</div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading && papers.length === 0 ? (
          <div className="rc-card">
            <Skeleton height={14} width="55%" />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={4} lineHeight={12} lastLineWidth="50%" />
          </div>
        ) : null}
        {!loading && papers.length === 0 ? <div className="rc-muted">No papers in this project yet.</div> : null}
        {papers.map((p) => (
          <div key={p.id} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <div style={{ fontWeight: 850, lineHeight: 1.25 }}>{p.title}</div>
              {p.processing_status === 'parsed' ? <span className="rc-badge rc-badge--success">parsed</span> : <span className="rc-badge">{p.processing_status || (p.is_processed ? 'processed' : 'uploaded')}</span>}
            </div>

            <div className="rc-help">
              {p.authors ? `${p.authors} · ` : ''}
              {p.journal ? `${p.journal} · ` : ''}
              {p.publication_year ? `${p.publication_year} · ` : ''}
              {p.doi ? `DOI: ${p.doi} · ` : ''}
              {p.pmid ? `PMID: ${p.pmid} · ` : ''}
              {p.filename}
              {p.file_size_kb ? ` · ${p.file_size_kb} KB` : ''}
              {p.source_provider ? ` · ${p.source_provider}` : ''}
              {p.is_open_access ? ' · OA' : ''}
            </div>
            {p.processing_warnings?.length ? <div className="rc-help">Warnings: {p.processing_warnings.join(', ')}</div> : null}

            <div className="rc-row" style={{ marginTop: 2 }}>
              <button className="rc-btn" onClick={() => downloadFile(p)}>Download PDF</button>
              <button className="rc-btn" onClick={() => processPaper(p)} disabled={p.is_processed}>Process</button>
              <button className="rc-btn rc-btn--primary" onClick={() => summarizePaper(p)}>Summarize</button>
              <button className="rc-btn rc-btn--ghost" onClick={() => deletePaper(p)} style={{ borderColor: 'rgba(185,28,28,0.25)', color: 'var(--rc-danger)' }}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

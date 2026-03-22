import { useEffect, useState } from 'react';
import type { BookRow } from '../types/api';
import { api } from '../services/api';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { useToast } from '../ui/Toast/ToastProvider';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';


export default function BooksPage() {
  const confirm = useConfirm();
  const toast = useToast();
  const [books, setBooks] = useState<BookRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [scanJobId, setScanJobId] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<{ status: string; progress: number; error?: string | null } | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/books');
      setBooks(r.data as BookRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load books');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!scanJobId) return;
    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${scanJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        setScanStatus({ status, progress, error: err });
        if (status === 'completed') {
          setScanJobId(null);
          await load();
        }
        if (status === 'failed') {
          setScanJobId(null);
        }
      } catch (e: any) {
        setScanStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    poll();
    const t = window.setInterval(poll, 4000);
    return () => {
      stopped = true;
      window.clearInterval(t);
    };
  }, [scanJobId]);

  async function scanFolder() {
    setError(null);
    setNotice(null);
    try {
      const r = await api.post('/books/scan-folder', {});
      const jid = String((r.data as any)?.job_id || '');
      setScanJobId(jid);
      setScanStatus({ status: 'queued', progress: 0, error: null });
      setNotice(`Scan job enqueued: ${jid}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Scan failed');
    }
  }

  async function upload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await api.post('/books/index', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      setNotice(`Index job enqueued: ${r.data?.job_id}`);
      setFile(null);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Upload/index failed');
    } finally {
      setUploading(false);
    }
  }

  async function reindex(b: BookRow) {
    setError(null);
    setNotice(null);
    try {
      const r = await api.post(`/books/${b.id}/reindex`);
      setNotice(`Re-index job enqueued: ${r.data?.job_id}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Re-index failed');
    }
  }

  async function del(b: BookRow) {
    const ok = await confirm({
      title: 'Delete book?',
      body: String(b.title || b.filename),
      confirmText: 'Delete',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    setNotice(null);
    try {
      await api.delete(`/books/${b.id}`);
      toast.success('Deleted', String(b.title || b.filename));
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Delete failed');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 980 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>Books</h2>
        <button onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {notice ? (
        <div style={{ fontSize: 12, background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.25)', padding: 8, borderRadius: 10 }}>
          {notice}
        </div>
      ) : null}
      {error ? <div style={{ color: 'crimson' }}>{String(error)}</div> : null}

      <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Index books from the server BOOKS folder (recommended)</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <button onClick={scanFolder} disabled={Boolean(scanJobId)}>
            {scanJobId ? 'Scanning…' : 'Scan BOOKS folder + index'}
          </button>
          {scanStatus ? (
            <span style={{ fontSize: 12, opacity: 0.8 }}>
              {scanStatus.status} · {scanStatus.progress}%
              {scanStatus.error ? <span style={{ color: 'crimson' }}> · {String(scanStatus.error)}</span> : null}
            </span>
          ) : null}
        </div>
        <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
          Put your PDFs in STORAGE_BASE_PATH/BOOKS on the server (no upload needed). Indexing runs async (RQ/Redis).
        </div>
      </div>

      <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Upload a book (optional)</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button onClick={upload} disabled={!file || uploading}>
            {uploading ? 'Uploading…' : 'Upload + index'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading && books.length === 0 ? (
          <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
            <Skeleton height={14} width="52%" radius={10} />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={3} lineHeight={12} lastLineWidth="45%" />
          </div>
        ) : null}
        {!loading && books.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 24px' }}>
            <svg width="88" height="88" viewBox="0 0 88 88" fill="none" style={{ margin: '0 auto 16px', display: 'block' }}>
              <rect x="10" y="14" width="44" height="58" rx="5" fill="rgba(59,130,246,0.07)" stroke="rgba(59,130,246,0.2)" strokeWidth="1.5"/>
              <rect x="18" y="8" width="44" height="58" rx="5" fill="rgba(59,130,246,0.06)" stroke="rgba(59,130,246,0.15)" strokeWidth="1.5"/>
              <rect x="26" y="2" width="44" height="58" rx="5" fill="var(--rc-surface)" stroke="rgba(59,130,246,0.22)" strokeWidth="1.5"/>
              <line x1="36" y1="16" x2="60" y2="16" stroke="rgba(59,130,246,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="36" y1="24" x2="60" y2="24" stroke="rgba(59,130,246,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="36" y1="32" x2="50" y2="32" stroke="rgba(59,130,246,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="36" y1="44" x2="60" y2="44" stroke="rgba(59,130,246,0.15)" strokeWidth="1" strokeLinecap="round"/>
              <line x1="36" y1="52" x2="55" y2="52" stroke="rgba(59,130,246,0.15)" strokeWidth="1" strokeLinecap="round"/>
              <circle cx="68" cy="70" r="16" fill="var(--rc-surface)" stroke="rgba(59,130,246,0.28)" strokeWidth="1.5"/>
              <path d="M64 70h8M68 66v8" stroke="rgba(59,130,246,0.65)" strokeWidth="2.2" strokeLinecap="round"/>
            </svg>
            <div style={{ fontWeight: 700, fontSize: 15, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}>No books indexed yet</div>
            <div style={{ fontSize: 13, color: 'var(--rc-muted)', marginTop: 5, maxWidth: 280, margin: '5px auto 0' }}>
              Place PDFs in <code style={{ background: 'rgba(59,130,246,0.08)', padding: '1px 5px', borderRadius: 4, fontSize: 12 }}>STORAGE_BASE_PATH/BOOKS</code> on the server to start indexing.
            </div>
          </div>
        ) : null}
        {books.map((b) => (
          <div key={b.id} style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
            <div style={{ fontWeight: 800 }}>{b.title || b.filename}</div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>
              {b.total_pages ? `${b.total_pages} pages · ` : ''}
              chapters: {b.chapters_count} · indexed_at: {b.indexed_at || '—'}
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={() => reindex(b)}>Re-index</button>
              <button onClick={() => del(b)} style={{ background: 'rgba(220,38,38,0.15)' }}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

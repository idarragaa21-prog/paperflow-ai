import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { BookRow } from '../types/api';
import { api } from '../services/api';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { useToast } from '../ui/Toast/ToastProvider';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';


export default function BooksPage() {
  const confirm = useConfirm();
  const toast = useToast();
  const qc = useQueryClient();

  const [file, setFile] = useState<File | null>(null);
  const [scanJobId, setScanJobId] = useState<string | null>(null);

  // ── Books list ────────────────────────────────────────────────────────────
  const { data: books = [], isLoading, error, refetch } = useQuery<BookRow[]>({
    queryKey: ['books'],
    queryFn: async () => (await api.get('/books')).data as BookRow[],
  });

  // ── Scan job polling ──────────────────────────────────────────────────────
  const { data: scanJob } = useQuery({
    queryKey: ['job', scanJobId],
    queryFn: async () => {
      const r = await api.get(`/jobs/${scanJobId}`);
      return r.data as { status: string; progress_percent: number; error?: string | null };
    },
    enabled: !!scanJobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (s === 'completed') { setScanJobId(null); qc.invalidateQueries({ queryKey: ['books'] }); return false; }
      if (s === 'failed') { setScanJobId(null); return false; }
      return 4000;
    },
  });

  const scanStatus = scanJob
    ? { status: scanJob.status, progress: scanJob.progress_percent, error: scanJob.error ?? null }
    : null;

  // ── Mutations ─────────────────────────────────────────────────────────────
  const scanMut = useMutation({
    mutationFn: async () => (await api.post('/books/scan-folder', {})).data,
    onSuccess: (data: any) => {
      const jid = String(data?.job_id || '');
      setScanJobId(jid);
      toast.success('Scan enqueued', `Job: ${jid}`);
    },
    onError: (e: any) => toast.error('Scan failed', e?.response?.data?.detail || 'Unknown error'),
  });

  const uploadMut = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file selected');
      const form = new FormData();
      form.append('file', file);
      return (await api.post('/books/index', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
    },
    onSuccess: (data: any) => {
      setFile(null);
      toast.success('Upload enqueued', `Job: ${data?.job_id}`);
      qc.invalidateQueries({ queryKey: ['books'] });
    },
    onError: (e: any) => toast.error('Upload failed', e?.response?.data?.detail || 'Unknown error'),
  });

  const reindexMut = useMutation({
    mutationFn: async (b: BookRow) => (await api.post(`/books/${b.id}/reindex`)).data,
    onSuccess: (data: any) => toast.success('Re-index enqueued', `Job: ${data?.job_id}`),
    onError: (e: any) => toast.error('Re-index failed', e?.response?.data?.detail || 'Unknown error'),
  });

  const deleteMut = useMutation({
    mutationFn: async (b: BookRow) => {
      const ok = await confirm({ title: 'Delete book?', body: String(b.title || b.filename), confirmText: 'Delete', danger: true });
      if (!ok) throw new Error('cancelled');
      await api.delete(`/books/${b.id}`);
      return b;
    },
    onSuccess: (b: BookRow) => {
      toast.success('Deleted', String(b.title || b.filename));
      qc.invalidateQueries({ queryKey: ['books'] });
    },
    onError: (e: any) => { if (e?.message !== 'cancelled') toast.error('Delete failed', e?.response?.data?.detail || 'Unknown error'); },
  });

  const errorMsg = error ? String((error as any)?.response?.data?.detail || 'Failed to load books') : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 980 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>Books</h2>
        <button onClick={() => refetch()} disabled={isLoading}>
          {isLoading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {errorMsg ? <div className="rc-error-card">{errorMsg}</div> : null}

      <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
        <div style={{ fontWeight: 800, marginBottom: 8 }}>Index books from the server BOOKS folder (recommended)</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <button onClick={() => scanMut.mutate()} disabled={!!scanJobId || scanMut.isPending}>
            {scanJobId ? 'Scanning…' : 'Scan BOOKS folder + index'}
          </button>
          {scanStatus ? (
            <span style={{ fontSize: 12, opacity: 0.8 }}>
              {scanStatus.status} · {scanStatus.progress}%
              {scanStatus.error ? <span className="rc-error"> · {String(scanStatus.error)}</span> : null}
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
          <button onClick={() => uploadMut.mutate()} disabled={!file || uploadMut.isPending}>
            {uploadMut.isPending ? 'Uploading…' : 'Upload + index'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {isLoading && books.length === 0 ? (
          <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 12 }}>
            <Skeleton height={14} width="52%" radius={10} />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={3} lineHeight={12} lastLineWidth="45%" />
          </div>
        ) : null}
        {!isLoading && books.length === 0 ? (
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
              chapters: {b.chapters?.length ?? 0} · indexed_at: {b.indexed_at || '—'}
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={() => reindexMut.mutate(b)}>Re-index</button>
              <button onClick={() => deleteMut.mutate(b)} style={{ background: 'rgba(220,38,38,0.15)' }}>
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

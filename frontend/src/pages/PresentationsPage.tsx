import { useEffect, useMemo, useState } from 'react';
import type { PaperRow } from '../types/api';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';

type PresentationRow = {
  id: string;
  title: string;
  topic: string;
  duration_minutes: number;
  audience: string;
  filename: string;
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

export default function PresentationsPage() {
  const { projectId } = useParams();

  const toast = useToast();

  const [papers, setPapers] = useState<PaperRow[]>([]);
  const [presentations, setPresentations] = useState<PresentationRow[]>([]);

  const [topic, setTopic] = useState('');
  const [audience, setAudience] = useState<'universidad' | 'palestra'>('universidad');
  const [durationMin, setDurationMin] = useState<number>(45);
  const [numSlides, setNumSlides] = useState<number>(35);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Record<string, boolean>>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const selectedIds = useMemo(() => Object.entries(selectedPaperIds).filter(([, v]) => v).map(([k]) => k), [selectedPaperIds]);

  async function loadAll() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const [p1, p2] = await Promise.all([
        api.get(`/papers/projects/${projectId}`),
        api.get(`/presentations/projects/${projectId}/presentations`),
      ]);
      setPapers((p1.data as any[]).map((p) => ({ id: p.id, title: p.title })) as PaperRow[]);
      setPresentations(p2.data as PresentationRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, [projectId]);

  async function generate() {
    if (!projectId) return;
    if (!topic.trim()) {
      setError('Topic is required');
      return;
    }
    if (selectedIds.length === 0) {
      setError('Select at least 1 paper');
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const r = await api.post('/presentations/generate', {
        project_id: projectId,
        topic: topic.trim(),
        duration_minutes: durationMin,
        audience,
        paper_ids: selectedIds,
        num_slides: numSlides,
      });
      toast.success('Job enqueued', `Presentation: ${String(r.data?.job_id || '')}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to enqueue presentation');
    } finally {
      setGenerating(false);
    }
  }

  async function downloadPresentation(p: PresentationRow) {
    setError(null);
    try {
      const r = await api.get(`/presentations/${p.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, p.filename || 'presentation.pptx');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Download failed');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Presentations</h1>
        <div className="rc-subtitle">Generate a 16:9 deck from selected papers. Jobs run async; download PPTX when ready.</div>
      </div>

      <div className="rc-row">
        <button onClick={loadAll} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Generate deck</div>

        <div className="rc-grid2">
          <div>
            <div className="rc-kicker">Topic</div>
            <input className="rc-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. ACL reconstruction: HT vs BPTB" />
          </div>
          <div>
            <div className="rc-kicker">Audience</div>
            <select className="rc-input" value={audience} onChange={(e) => setAudience(e.target.value as any)}>
              <option value="universidad">University</option>
              <option value="palestra">Conference</option>
            </select>
          </div>
          <div>
            <div className="rc-kicker">Duration (min)</div>
            <input className="rc-input" type="number" value={durationMin} onChange={(e) => setDurationMin(Number(e.target.value))} />
          </div>
          <div>
            <div className="rc-kicker"># Slides (20–50)</div>
            <input className="rc-input" type="number" min={20} max={50} value={numSlides} onChange={(e) => setNumSlides(Number(e.target.value))} />
          </div>
        </div>

        <div style={{ height: 12 }} />
        <div className="rc-kicker" style={{ marginBottom: 6 }}>Select papers (max 10)</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflow: 'auto', padding: 8, borderRadius: 12, border: '1px solid var(--rc-border)', background: 'var(--rc-bg)' }}>
          {papers.map((p) => (
            <label key={p.id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <input
                type="checkbox"
                checked={Boolean(selectedPaperIds[p.id])}
                onChange={(e) => setSelectedPaperIds((s) => ({ ...s, [p.id]: e.target.checked }))}
                style={{ marginTop: 3 }}
              />
              <span style={{ lineHeight: 1.3 }}>{p.title}</span>
            </label>
          ))}
          {papers.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--rc-muted)' }}>
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" style={{ margin: '0 auto 10px', display: 'block' }}>
                <rect x="6" y="8" width="28" height="34" rx="4" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
                <line x1="12" y1="18" x2="28" y2="18" stroke="rgba(99,102,241,0.25)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="12" y1="24" x2="28" y2="24" stroke="rgba(99,102,241,0.25)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="12" y1="30" x2="22" y2="30" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <div style={{ fontSize: 13, fontWeight: 600 }}>No papers in this project yet</div>
              <div style={{ fontSize: 12, marginTop: 3 }}>Add papers to the library first</div>
            </div>
          ) : null}
        </div>

        <div style={{ height: 12 }} />
        <button disabled={generating} onClick={generate}>
          {generating ? 'Enqueueing…' : 'Generate'}
        </button>
        <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
          Tip: for a “non-generic” deck, select &gt;=3 key papers (RCT + meta-analysis if possible).
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontWeight: 850 }}>Decks</div>
        {presentations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '48px 24px' }}>
            <svg width="72" height="72" viewBox="0 0 72 72" fill="none" style={{ margin: '0 auto 14px', display: 'block' }}>
              <rect x="6" y="14" width="60" height="40" rx="5" fill="rgba(99,102,241,0.07)" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5"/>
              <rect x="12" y="20" width="48" height="28" rx="3" fill="rgba(99,102,241,0.05)" stroke="rgba(99,102,241,0.15)" strokeWidth="1"/>
              <line x1="20" y1="28" x2="52" y2="28" stroke="rgba(99,102,241,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="20" y1="34" x2="52" y2="34" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="20" y1="40" x2="40" y2="40" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="30" y1="54" x2="42" y2="54" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="36" y1="54" x2="36" y2="60" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <div style={{ fontWeight: 700, fontSize: 15, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}>No presentations yet</div>
            <div style={{ fontSize: 13, color: 'var(--rc-muted)', marginTop: 5 }}>Select papers and generate your first presentation</div>
          </div>
        ) : null}
        {presentations.map((p) => (
          <div key={p.id} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontWeight: 750 }}>{p.title}</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>
              {p.topic} · {p.audience} · {p.duration_minutes} min · {p.filename}
            </div>
            <div className="rc-row">
              <button onClick={() => downloadPresentation(p)}>Download PPTX</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

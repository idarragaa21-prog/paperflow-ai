import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';

type PaperRow = {
  id: string;
  title: string;
};

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

      {error ? <div className="rc-danger">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Generate deck</div>

        <div className="rc-grid2">
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Topic</div>
            <input value={topic} onChange={(e) => setTopic(e.target.value)} style={{ width: '100%' }} placeholder="e.g. ACL reconstruction: HT vs BPTB" />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Audience</div>
            <select value={audience} onChange={(e) => setAudience(e.target.value as any)} style={{ width: '100%' }}>
              <option value="universidad">universidad</option>
              <option value="palestra">palestra</option>
            </select>
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>Duration (min)</div>
            <input type="number" value={durationMin} onChange={(e) => setDurationMin(Number(e.target.value))} style={{ width: '100%' }} />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.8 }}># Slides (20–50)</div>
            <input type="number" min={20} max={50} value={numSlides} onChange={(e) => setNumSlides(Number(e.target.value))} style={{ width: '100%' }} />
          </div>
        </div>

        <div style={{ height: 12 }} />
        <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 6 }}>Select papers (max 10)</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 240, overflow: 'auto', padding: 8, borderRadius: 12, border: '1px solid rgba(15, 23, 42, 0.10)', background: 'rgba(2, 6, 23, 0.02)' }}>
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
          {papers.length === 0 ? <div className="rc-muted">No papers available yet.</div> : null}
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
        {presentations.length === 0 ? <div className="rc-muted">No presentations yet.</div> : null}
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

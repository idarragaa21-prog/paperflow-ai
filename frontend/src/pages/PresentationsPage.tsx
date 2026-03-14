import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';

type PaperRow = {
  id: string;
  title: string;
};

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
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
        api.get(`/papers/projects/${projectId}`, { params: { limit: 100 } }),
        api.get(`/presentations/projects/${projectId}/presentations`),
      ]);
      const page = p1.data as PaginatedResponse<any>;
      setPapers((page.items || []).map((p) => ({ id: p.id, title: p.title })) as PaperRow[]);
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
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Presentations</div>
          <h2>Genera decks a partir de papers seleccionados</h2>
          <p>Convierte un conjunto de papers en una presentación 16:9 lista para descargar cuando el job termine.</p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{papers.length} papers disponibles</span>
          <span className="rc-discover-badge">{presentations.length} decks generados</span>
        </div>
      </div>

      {error ? <div className="rc-danger">{String(error)}</div> : null}

      <div className="rc-product-two-column rc-product-two-column--wide">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Generar deck</div>
              <div className="rc-help">Selecciona papers clave y ajusta audiencia, duración y número de diapositivas.</div>
            </div>
            <button className="rc-btn rc-btn--subtle" onClick={loadAll} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>

          <div className="rc-product-form-grid rc-product-form-grid--three">
            <label className="rc-discover-filter-field">
              <span>Topic</span>
              <input className="rc-input" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. ACL reconstruction: HT vs BPTB" />
            </label>
            <label className="rc-discover-filter-field">
              <span>Audience</span>
              <select className="rc-input" value={audience} onChange={(e) => setAudience(e.target.value as any)}>
              <option value="universidad">universidad</option>
              <option value="palestra">palestra</option>
            </select>
            </label>
            <label className="rc-discover-filter-field">
              <span>Duration (min)</span>
              <input className="rc-input" type="number" value={durationMin} onChange={(e) => setDurationMin(Number(e.target.value))} />
            </label>
            <label className="rc-discover-filter-field">
              <span># Slides (20–50)</span>
              <input className="rc-input" type="number" min={20} max={50} value={numSlides} onChange={(e) => setNumSlides(Number(e.target.value))} />
            </label>
          </div>

          <div className="rc-help" style={{ marginBottom: 8 }}>Select papers (max 10)</div>
          <div className="rc-product-selection-list">
          {papers.map((p) => (
            <label key={p.id} className="rc-product-selection-option">
              <input
                type="checkbox"
                checked={Boolean(selectedPaperIds[p.id])}
                onChange={(e) => setSelectedPaperIds((s) => ({ ...s, [p.id]: e.target.checked }))}
              />
              <span style={{ lineHeight: 1.3 }}>{p.title}</span>
            </label>
          ))}
          {papers.length === 0 ? <div className="rc-muted">No papers available yet.</div> : null}
          </div>

          <div className="rc-product-actions">
            <button className="rc-btn rc-btn--primary" disabled={generating} onClick={generate}>
              {generating ? 'Enqueueing…' : 'Generate'}
            </button>
          </div>
          <div className="rc-help">Tip: para un deck menos genérico, selecciona al menos 3 papers clave.</div>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div className="rc-card-title">Decks</div>
          </div>
          {presentations.length === 0 ? <div className="rc-empty-state">No presentations yet.</div> : null}
          <div className="rc-product-record-list">
            {presentations.map((p) => (
              <div key={p.id} className="rc-product-record rc-product-record--soft">
                <div style={{ fontWeight: 750 }}>{p.title}</div>
                <div className="rc-help">
                  {p.topic} · {p.audience} · {p.duration_minutes} min · {p.filename}
                </div>
                <div className="rc-product-actions" style={{ marginTop: 10 }}>
                  <button className="rc-btn" onClick={() => downloadPresentation(p)}>Download PPTX</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

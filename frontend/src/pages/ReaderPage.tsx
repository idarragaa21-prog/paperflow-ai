import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, requestTimeouts } from '../services/api';

type PaperOption = {
  id: string;
  title: string;
  processing_status: string;
};

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

type Citation = {
  paper_id: string;
  page?: number | null;
  locator?: Record<string, unknown> | null;
  quoted_text: string;
};

type ChatResult = {
  session_id: string;
  answer: string;
  claim_type: string;
  confidence: number;
  grounded: boolean;
  citations: Citation[];
  blocked_reason?: string | null;
  dependency_error_code?: string | null;
  grounding_score?: number | null;
};

const QUESTION_PRESETS = [
  'Resume los hallazgos principales con evidencia.',
  'Que resultados reporta este articulo?',
  'Cuales son las limitaciones principales?',
  'Compara las conclusiones entre los papers disponibles.',
];

export default function ReaderPage() {
  const { projectId } = useParams();
  const [papers, setPapers] = useState<PaperOption[]>([]);
  const [paperId, setPaperId] = useState<string>('project');
  const [question, setQuestion] = useState('Resume los hallazgos principales con evidencia.');
  const [result, setResult] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestState, setRequestState] = useState<'idle' | 'loading' | 'success' | 'blocked' | 'dependency_error' | 'error'>('idle');

  async function loadPapers() {
    if (!projectId) return;
    setError(null);
    const response = await api.get(`/projects/${projectId}/library`, { params: { limit: 100 } });
    const page = response.data as PaginatedResponse<PaperOption>;
    setPapers(page.items);
  }

  useEffect(() => {
    loadPapers().catch((e: any) => setError(e?.response?.data?.detail || 'No se pudo cargar la biblioteca'));
  }, [projectId]);

  async function askQuestion() {
    if (!projectId || !question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setRequestState('loading');
    try {
      const payload = { question, task_type: 'chat', max_citations: 4 };
      const response =
        paperId === 'project'
          ? await api.post(`/projects/${projectId}/chat`, payload, { timeout: requestTimeouts.chat })
          : await api.post(`/papers/${paperId}/chat`, payload, { timeout: requestTimeouts.chat });
      const nextResult = response.data as ChatResult;
      setResult(nextResult);
      if (nextResult.dependency_error_code) {
        setRequestState('dependency_error');
      } else if (nextResult.blocked_reason) {
        setRequestState('blocked');
      } else {
        setRequestState('success');
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La consulta al lector fallo');
      setRequestState('error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--warm">Paso 2 · Leer y preguntar</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Lee articulos con la evidencia a la vista</h1>
          <div className="rc-subtitle">Pregunta sobre un articulo o sobre todo el proyecto. Las respuestas se mantienen ancladas a la evidencia recuperada y se bloquean cuando el soporte es debil.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>Usa esta vista para entender los hallazgos antes de extraer o escribir. Aqui importa la confianza, no la velocidad.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{papers.length}</strong><span>Articulos disponibles</span></div>
          <div className="rc-metric-tile"><strong>{result ? result.citations.length : '—'}</strong><span>Citas en la respuesta</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-shelf">
        <div className="rc-card">
          <div className="rc-card-title">Haz una pregunta</div>
          <div className="rc-help" style={{ marginBottom: 12 }}>Empieza por una pregunta corta y concreta. Si quieres comparar varios papers, deja el alcance en todo el proyecto.</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">Alcance</div>
              <select data-testid="reader-scope-select" className="rc-input" value={paperId} onChange={(e) => setPaperId(e.target.value)}>
                <option value="project">Todo el proyecto</option>
                {papers.map((paper) => (
                  <option key={paper.id} value={paper.id}>
                    {paper.title} · {paper.processing_status}
                  </option>
                ))}
              </select>
            </div>
            <button data-testid="reader-refresh-papers" className="rc-btn" onClick={() => loadPapers()} disabled={loading}>Actualizar articulos</button>
            <button data-testid="reader-ask-button" className="rc-btn rc-btn--primary" onClick={askQuestion} disabled={loading || !question.trim()}>
              {loading ? 'Preguntando…' : 'Preguntar'}
            </button>
          </div>
          <div style={{ height: 10 }} />
          <div className="rc-chip-list" style={{ marginBottom: 12 }}>
            {QUESTION_PRESETS.map((preset) => (
              <button key={preset} className="rc-chip rc-chip--button" type="button" onClick={() => setQuestion(preset)}>
                {preset}
              </button>
            ))}
          </div>
          <textarea
            data-testid="reader-question-input"
            className="rc-input"
            style={{ minHeight: 120, width: '100%' }}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <div className="rc-row" style={{ marginTop: 12 }}>
            <Link className="rc-btn" to={`/projects/${projectId}/library`}>Abrir biblioteca</Link>
            <Link className="rc-btn rc-btn--primary" to={`/projects/${projectId}/meta`}>Ir a extraccion</Link>
          </div>
        </div>

        <div data-testid="reader-answer-panel" className="rc-card">
          <div className="rc-card-title">Respuesta</div>
          {requestState === 'loading' ? <div className="rc-help">Consultando la evidencia recuperada…</div> : null}
          {!result && requestState !== 'loading' ? <div className="rc-muted">Todavia no hay respuesta.</div> : null}
          {result ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {result.dependency_error_code ? (
                <div className="rc-error">
                  El lector no pudo responder por un problema de infraestructura ({result.dependency_error_code}).
                </div>
              ) : null}
              {result.blocked_reason ? (
                <div className="rc-help">
                  Respuesta bloqueada por evidencia insuficiente ({result.blocked_reason}).
                </div>
              ) : null}
              <div className="rc-help" data-testid="reader-answer-state">
                {result.claim_type} · confianza {result.confidence.toFixed(2)} · {result.grounded ? 'con evidencia' : (result.dependency_error_code ? 'fallo de dependencia' : 'sin evidencia suficiente')}
              </div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{result.answer}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {result.citations.map((citation, index) => (
                  <div key={`${citation.paper_id}-${index}`} className="rc-soft-card">
                    <div className="rc-kicker">Cita {index + 1}</div>
                    <div className="rc-help">Paper {citation.paper_id} · pagina {citation.page ?? '—'}</div>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{citation.quoted_text}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

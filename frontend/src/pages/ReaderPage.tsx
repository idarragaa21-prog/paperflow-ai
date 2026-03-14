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
  '¿Qué resultados reporta este artículo?',
  '¿Cuáles son las limitaciones principales?',
  'Compara las conclusiones entre los papers disponibles.',
];

export default function ReaderPage() {
  const { projectId } = useParams();
  const [papers, setPapers] = useState<PaperOption[]>([]);
  const [paperId, setPaperId] = useState<string>('project');
  const [question, setQuestion] = useState('Resume los hallazgos principales con evidencia.');
  const [result, setResult] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [paperLoading, setPaperLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requestState, setRequestState] = useState<'idle' | 'loading' | 'success' | 'blocked' | 'dependency_error' | 'error'>('idle');

  async function loadPapers() {
    if (!projectId) return;
    setPaperLoading(true);
    setError(null);
    try {
      const loadedPapers: PaperOption[] = [];
      const seen = new Set<string>();
      let cursor: string | null = null;
      let hasMore = true;

      while (hasMore) {
        const response = await api.get(`/projects/${projectId}/library`, {
          params: { limit: 100, cursor: cursor || undefined },
        });
        const page = response.data as PaginatedResponse<PaperOption>;
        for (const paper of page.items) {
          if (seen.has(paper.id)) continue;
          seen.add(paper.id);
          loadedPapers.push(paper);
        }
        cursor = page.next_cursor || null;
        hasMore = Boolean(page.has_more && cursor);
      }

      setPapers(loadedPapers);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo cargar la biblioteca');
    } finally {
      setPaperLoading(false);
    }
  }

  useEffect(() => {
    void loadPapers();
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
      setError(e?.response?.data?.detail || 'La consulta al lector falló');
      setRequestState('error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Chat grounded</div>
          <h2>Pregunta sobre un paper o sobre todo el proyecto</h2>
          <p>
            Usa el lector para revisar evidencia antes de extraer o redactar. El sistema responde con citas o falla de
            forma explícita cuando la evidencia o la infraestructura no alcanzan.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{papers.length} artículos disponibles</span>
          <span className="rc-discover-badge">{result ? `${result.citations.length} citas` : 'Sin respuesta aún'}</span>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Haz una pregunta</div>
              <div className="rc-help">Empieza por una pregunta corta y decide si quieres leer a nivel paper o proyecto.</div>
            </div>
            <button
              data-testid="reader-refresh-papers"
              className="rc-btn rc-btn--subtle"
              onClick={() => void loadPapers()}
              disabled={paperLoading || loading}
            >
              {paperLoading ? 'Actualizando…' : 'Actualizar artículos'}
            </button>
          </div>

          <div className="rc-product-form-grid">
            <label className="rc-discover-filter-field">
              <span>Alcance</span>
              <select
                data-testid="reader-scope-select"
                className="rc-input"
                value={paperId}
                onChange={(event) => setPaperId(event.target.value)}
              >
                <option value="project">Todo el proyecto</option>
                {papers.map((paper) => (
                  <option key={paper.id} value={paper.id}>
                    {paper.title} · {paper.processing_status}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rc-chip-list">
            {QUESTION_PRESETS.map((preset) => (
              <button key={preset} className="rc-discover-mini-chip" type="button" onClick={() => setQuestion(preset)}>
                {preset}
              </button>
            ))}
          </div>

          <textarea
            data-testid="reader-question-input"
            className="rc-discover-composer__input rc-product-textarea"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />

          <div className="rc-row">
            <button
              data-testid="reader-ask-button"
              className="rc-btn rc-btn--primary"
              onClick={() => void askQuestion()}
              disabled={loading || !question.trim()}
            >
              {loading ? 'Preguntando…' : 'Preguntar'}
            </button>
            <Link className="rc-btn rc-btn--subtle" to={`/projects/${projectId}/library`}>
              Abrir biblioteca
            </Link>
            <Link className="rc-btn rc-btn--subtle" to={`/projects/${projectId}/meta`}>
              Ir a extracción
            </Link>
          </div>
        </section>

        <section data-testid="reader-answer-panel" className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Respuesta</div>
              <div className="rc-help">
                {requestState === 'loading'
                  ? 'Consultando la evidencia recuperada…'
                  : 'Aquí verás si la respuesta fue grounded, bloqueada o si falló una dependencia.'}
              </div>
            </div>
          </div>

          {!result && requestState !== 'loading' ? <div className="rc-muted">Todavia no hay respuesta.</div> : null}
          {result ? (
            <div className="rc-product-answer">
              {result.dependency_error_code ? (
                <div className="rc-error">
                  El lector no pudo responder por un problema de infraestructura ({result.dependency_error_code}).
                </div>
              ) : null}
              {result.blocked_reason ? (
                <div className="rc-help">Respuesta bloqueada por evidencia insuficiente ({result.blocked_reason}).</div>
              ) : null}

              <div className="rc-help" data-testid="reader-answer-state">
                {result.claim_type} · confianza {result.confidence.toFixed(2)} ·{' '}
                {result.grounded
                  ? 'con evidencia'
                  : result.dependency_error_code
                    ? 'fallo de dependencia'
                    : 'sin evidencia suficiente'}
              </div>

              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.65 }}>{result.answer}</div>

              <div className="rc-product-citation-list">
                {result.citations.map((citation, index) => (
                  <div key={`${citation.paper_id}-${index}`} className="rc-product-citation">
                    <div className="rc-kicker">Cita {index + 1}</div>
                    <div className="rc-help">
                      Paper {citation.paper_id} · página {citation.page ?? '—'}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>{citation.quoted_text}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

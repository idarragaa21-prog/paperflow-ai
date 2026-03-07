import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

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
};

export default function ReaderPage() {
  const { projectId } = useParams();
  const [papers, setPapers] = useState<PaperOption[]>([]);
  const [paperId, setPaperId] = useState<string>('project');
  const [question, setQuestion] = useState('Summarize the main findings with evidence.');
  const [result, setResult] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadPapers() {
    if (!projectId) return;
    const response = await api.get(`/projects/${projectId}/library`, { params: { limit: 100 } });
    const page = response.data as PaginatedResponse<PaperOption>;
    setPapers(page.items);
  }

  useEffect(() => {
    loadPapers().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load library'));
  }, [projectId]);

  async function askQuestion() {
    if (!projectId || !question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const payload = { question, task_type: 'chat', max_citations: 4 };
      const response =
        paperId === 'project'
          ? await api.post(`/projects/${projectId}/chat`, payload)
          : await api.post(`/papers/${paperId}/chat`, payload);
      setResult(response.data as ChatResult);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Chat failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Reader</h1>
        <div className="rc-subtitle">Grounded chat on one paper or the whole project. Answers are blocked when support is too weak.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Ask a question</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Scope</div>
            <select data-testid="reader-scope-select" className="rc-input" value={paperId} onChange={(e) => setPaperId(e.target.value)}>
              <option value="project">Whole project</option>
              {papers.map((paper) => (
                <option key={paper.id} value={paper.id}>
                  {paper.title} · {paper.processing_status}
                </option>
              ))}
            </select>
          </div>
          <button data-testid="reader-refresh-papers" className="rc-btn" onClick={() => loadPapers()} disabled={loading}>Refresh papers</button>
          <button data-testid="reader-ask-button" className="rc-btn rc-btn--primary" onClick={askQuestion} disabled={loading || !question.trim()}>
            {loading ? 'Asking…' : 'Ask'}
          </button>
        </div>
        <div style={{ height: 10 }} />
        <textarea
          data-testid="reader-question-input"
          className="rc-input"
          style={{ minHeight: 120, width: '100%' }}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
      </div>

      <div data-testid="reader-answer-panel" className="rc-card">
        <div className="rc-card-title">Answer</div>
        {!result ? <div className="rc-muted">No answer yet.</div> : null}
        {result ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="rc-help">
              {result.claim_type} · confidence {result.confidence.toFixed(2)} · {result.grounded ? 'grounded' : 'not grounded'}
            </div>
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{result.answer}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {result.citations.map((citation, index) => (
                <div key={`${citation.paper_id}-${index}`} className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">Citation {index + 1}</div>
                  <div className="rc-help">Paper {citation.paper_id} · page {citation.page ?? '—'}</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{citation.quoted_text}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

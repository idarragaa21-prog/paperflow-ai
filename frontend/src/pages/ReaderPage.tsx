import { useCallback, useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../services/api';
import { EmptyState } from '../components/EmptyState';
import { InsightCard, PageHero } from '../components/WorkflowPrimitives';

type PaperOption = {
  id: string;
  title: string;
  processing_status: string;
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

type HistoryItem = {
  role: 'user' | 'assistant';
  question?: string;
  result?: ChatResult;
};

function StatusDot({ status }: { status: string }) {
  const s = (status || 'uploaded').toLowerCase();
  if (s === 'ready' || s === 'parsed') return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a' }} /> Ready for chat</span>;
  if (s === 'processing' || s === 'queued') return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }} /> Processing\u2026</span>;
  if (s === 'failed') return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#b91c1c' }} /> Processing failed</span>;
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#d97706' }} /> Not processed yet</span>;
}

function BouncingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--rc-primary)',
          animation: `bounce-dot 1s ${i * 0.15}s infinite ease-in-out`,
        }} />
      ))}
      <style>{`@keyframes bounce-dot { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-8px)} }`}</style>
    </span>
  );
}

const SUGGESTED_QUESTIONS = [
  'What are the main findings and limitations?',
  'Which outcomes showed the strongest evidence?',
  'Summarize the cohort, intervention and comparator.',
  'What caveats should I keep in mind before extraction?',
];

export default function ReaderPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [papers, setPapers] = useState<PaperOption[]>([]);
  const [papersLoading, setPapersLoading] = useState(true);
  const [paperId, setPaperId] = useState<string>('project');
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const selectedPaper = papers.find(p => p.id === paperId);
  const selectedStatus = selectedPaper?.processing_status || '';
  const isProject = paperId === 'project';
  const hasReadyPapers = papers.some(p => ['ready', 'parsed'].includes((p.processing_status || '').toLowerCase()));
  const selectedPaperReady = ['ready', 'parsed'].includes(selectedStatus.toLowerCase());
  const canAsk = question.trim().length > 0 && (isProject ? hasReadyPapers : selectedPaperReady);
  const latestAssistantResult = [...history].reverse().find((item) => item.role === 'assistant' && item.result?.claim_type !== 'error')?.result;

  const loadPapers = useCallback(async () => {
    if (!projectId) return;
    setPapersLoading(true);
    try {
      const response = await api.get(`/projects/${projectId}/library`);
      setPapers(response.data as PaperOption[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Error cargando library');
    } finally {
      setPapersLoading(false);
    }
  }, [projectId]);

  useEffect(() => { void loadPapers(); }, [loadPapers]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [history, loading]);

  async function processNow(id: string) {
    setError(null);
    try {
      await api.post(`/papers/${id}/process`);
      await loadPapers();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Error al procesar'); }
  }

  async function askQuestion() {
    if (!projectId || !question.trim()) return;
    setLoading(true); setError(null);
    const q = question.trim();
    setHistory(prev => [...prev, { role: 'user', question: q }]);
    setQuestion('');
    try {
      const payload = { question: q, task_type: 'chat', max_citations: 4 };
      const response = paperId === 'project'
        ? await api.post(`/projects/${projectId}/chat`, payload)
        : await api.post(`/papers/${paperId}/chat`, payload);
      const result = response.data as ChatResult;
      setHistory(prev => [...prev, { role: 'assistant', result }]);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Chat failed. The LLM service may be unavailable.';
      setError(msg);
      setHistory(prev => [...prev, { role: 'assistant', result: { session_id: '', answer: `Error: ${msg}`, claim_type: 'error', confidence: 0, grounded: false, citations: [] } }]);
    } finally { setLoading(false); }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); askQuestion(); }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <PageHero
        eyebrow="Stage 3 · Reader"
        title="Read with AI, but keep the evidence surface visible"
        subtitle="Use grounded chat on one paper or the whole project. The goal is not generic answers, but decisions backed by extractable evidence."
        metrics={[
          { label: 'papers in scope', value: papers.length, tone: 'primary' },
          { label: 'ready for chat', value: papers.filter(p => ['ready', 'parsed'].includes((p.processing_status || '').toLowerCase())).length, tone: 'success' },
          { label: 'conversation turns', value: history.length, tone: 'neutral' },
        ]}
      />

      {error && <div className="rc-error">{error}</div>}

      {papersLoading && (
        <div className="rc-page-skeleton">
          <div className="rc-skeleton-card">
            <div className="rc-skeleton-line" style={{ width: '40%', height: 12 }} />
            <div className="rc-skeleton-line" style={{ width: '70%', height: 32 }} />
          </div>
          <div className="rc-skeleton-card" style={{ minHeight: 200 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 20 }}>
              {[80, 60, 90, 50].map((w, i) => (
                <div key={i} className="rc-skeleton-line" style={{ width: `${w}%` }} />
              ))}
            </div>
          </div>
        </div>
      )}

      {!papersLoading && papers.length === 0 && (
        <EmptyState
          variant="papers"
          title="No papers in this project yet"
          description="Add PDFs to your library first. Once processed, you can ask questions grounded in the full text."
          action={
            <button
              className="rc-btn rc-btn--primary"
              onClick={() => navigate(`/projects/${projectId}/library`)}
            >
              Go to Library →
            </button>
          }
        />
      )}

      {!papersLoading && papers.length > 0 && (
        <div className="rc-composer-shell">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="rc-card">
              <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap', gap: 10 }}>
                <div style={{ minWidth: 260, flex: 1 }}>
                  <div className="rc-kicker">Scope</div>
                  <select
                    className="rc-input"
                    data-testid="reader-scope-select"
                    value={paperId}
                    onChange={e => setPaperId(e.target.value)}
                  >
                    <option value="project">Whole project</option>
                    {papers.map(paper => (
                      <option key={paper.id} value={paper.id}>{paper.title}</option>
                    ))}
                  </select>
                </div>
                <button className="rc-btn" onClick={loadPapers} style={{ padding: '8px 12px', fontSize: 12 }}>Refresh</button>
              </div>

              <div style={{ marginTop: 10 }}>
                {!isProject && selectedPaper && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <StatusDot status={selectedStatus} />
                    {['processing', 'queued'].includes(selectedStatus.toLowerCase()) && (
                      <span className="rc-help">This paper is still being processed. Chat will be available soon.</span>
                    )}
                    {(!selectedStatus || selectedStatus === 'uploaded') && (
                      <button className="rc-btn" data-testid="reader-process-now" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => processNow(paperId)}>Process now</button>
                    )}
                    {selectedStatus === 'failed' && (
                      <button className="rc-btn" data-testid="reader-process-now" style={{ padding: '4px 10px', fontSize: 11 }} onClick={() => processNow(paperId)}>Retry processing</button>
                    )}
                  </div>
                )}
                {isProject && !hasReadyPapers && papers.length > 0 && (
                  <div className="rc-card" style={{ background: 'rgba(217,119,6,0.08)', border: '1px solid rgba(217,119,6,0.2)', marginTop: 8 }}>
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>No processed papers in this project yet.</div>
                    <div className="rc-help" style={{ marginBottom: 8 }}>Go to Library, select papers, and click Process.</div>
                    <button className="rc-btn" style={{ padding: '6px 12px', fontSize: 12 }} onClick={() => navigate(`/projects/${projectId}/library`)}>Go to Library</button>
                  </div>
                )}
              </div>
            </div>

            <div
              className="rc-card"
              data-testid="reader-answer-panel"
              style={{ minHeight: 320, maxHeight: 520, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10, padding: 14 }}
            >
              {history.length === 0 && !loading && (
                <div style={{ textAlign: 'center', padding: '40px 24px', color: 'var(--rc-muted)' }}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--rc-border-strong)" strokeWidth="1.5" strokeLinecap="round" style={{ marginBottom: 10, display: 'block', margin: '0 auto 12px' }}>
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>No conversation yet</div>
                  <div style={{ fontSize: 12 }}>Ask a question about the {isProject ? 'project papers' : 'selected paper'} below.</div>
                </div>
              )}
              {history.map((item, i) => (
                <ChatBubble key={i} item={item} />
              ))}
              {loading && (
                <div style={{ alignSelf: 'flex-start', background: 'var(--rc-bg)', padding: '10px 16px', borderRadius: 14 }}>
                  <BouncingDots />
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="rc-kicker">Suggested prompts</div>
              <div className="rc-row" style={{ gap: 8 }}>
                {SUGGESTED_QUESTIONS.map((prompt) => (
                  <button
                    key={prompt}
                    className="rc-btn rc-btn--sm"
                    onClick={() => setQuestion(prompt)}
                    style={{ justifyContent: 'flex-start' }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
              <div className="rc-row" style={{ gap: 8 }}>
                <textarea
                  className="rc-input"
                  data-testid="reader-question-input"
                  style={{ flex: 1, minHeight: 48, maxHeight: 120, resize: 'vertical', fontSize: 13 }}
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Ask a question... (Enter to send)"
                />
                <button
                  className="rc-btn rc-btn--primary"
                  data-testid="reader-ask-button"
                  onClick={askQuestion}
                  disabled={loading || !canAsk}
                  style={{ alignSelf: 'flex-end', padding: '10px 16px' }}
                >
                  {loading ? '...' : 'Ask'}
                </button>
              </div>
            </div>
          </div>

          <div className="rc-workspace-rail">
            <InsightCard
              eyebrow="Reading mode"
              title={isProject ? 'Whole project scope' : selectedPaper?.title || 'Single paper scope'}
              body={isProject
                ? 'Project scope is best for synthesis questions after you already processed enough papers.'
                : 'Single-paper mode is best when you need precise support before extracting or citing.'}
              tone="primary"
              action={projectId ? <Link className="rc-btn rc-btn--sm" style={{ textDecoration: 'none' }} to={`/projects/${projectId}/meta`}>Go to Extraction</Link> : undefined}
            />

            <InsightCard
              eyebrow="Evidence rail"
              title={latestAssistantResult?.citations.length ? `${latestAssistantResult.citations.length} citation(s) in latest answer` : 'No citations yet'}
              body={latestAssistantResult?.citations.length
                ? 'Use the latest grounded answer to decide what should become notes, extraction targets or writing inputs.'
                : 'Citations will appear here as soon as the assistant can ground an answer in processed evidence.'}
              tone={latestAssistantResult?.citations.length ? 'success' : 'neutral'}
            />

            {latestAssistantResult?.citations.length ? (
              <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div className="rc-card-title" style={{ marginBottom: 0 }}>Latest citations</div>
                {latestAssistantResult.citations.slice(0, 4).map((citation, index) => (
                  <div key={`${citation.paper_id}-${index}`} style={{ padding: 10, borderRadius: 12, background: 'var(--rc-surface-2)', fontSize: 12 }}>
                    <div className="rc-help">Citation {index + 1} · page {citation.page ?? '—'}</div>
                    <div style={{ marginTop: 4, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{citation.quoted_text}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

function ChatBubble({ item }: { item: HistoryItem }) {
  const [showCitations, setShowCitations] = useState(false);

  if (item.role === 'user') {
    return (
      <div style={{ alignSelf: 'flex-end', background: 'var(--rc-primary-weak)', padding: '10px 14px', borderRadius: '14px 14px 4px 14px', maxWidth: '75%' }}>
        <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{item.question}</div>
      </div>
    );
  }

  const r = item.result;
  if (!r) return null;
  const isError = r.claim_type === 'error';

  return (
    <div style={{ alignSelf: 'flex-start', background: 'var(--rc-bg)', padding: '10px 14px', borderRadius: '14px 14px 14px 4px', maxWidth: '85%', border: '1px solid var(--rc-border)' }}>
      <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55, fontSize: 13, color: isError ? 'var(--rc-danger)' : undefined }}>{r.answer}</div>
      {!isError && (
        <div style={{ marginTop: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
          <span className="rc-badge" style={{ fontSize: 10 }}>conf {r.confidence.toFixed(2)}</span>
          {r.grounded && <span className="rc-badge rc-badge--success" style={{ fontSize: 10 }}>grounded</span>}
          {r.citations.length > 0 && (
            <button className="rc-btn" style={{ padding: '2px 8px', fontSize: 10 }} onClick={() => setShowCitations(!showCitations)}>
              {showCitations ? 'Hide' : 'Show'} {r.citations.length} citation{r.citations.length !== 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}
      {showCitations && r.citations.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {r.citations.map((c, ci) => (
            <div key={ci} style={{ fontSize: 11, padding: '6px 10px', background: 'rgba(0,0,0,0.03)', borderRadius: 8 }}>
              <div className="rc-help">Citation {ci + 1} &middot; page {c.page ?? '\u2014'}</div>
              <div style={{ whiteSpace: 'pre-wrap', marginTop: 2 }}>{c.quoted_text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

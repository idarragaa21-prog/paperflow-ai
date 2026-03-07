import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';

type Batch = { id: string; title: string; stage: string; status: string };
type Reason = { id: string; code: string; label: string };
type Paper = { id: string; title: string };
type Comment = { id: string; user_id: string; body: string; target_type?: string | null; target_id?: string | null };
type PeerReviewAction = { id: string; user_id: string; action: string; status: string; payload_json?: Record<string, unknown> | null };

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

export default function ScreeningPage() {
  const { projectId } = useParams();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [reasons, setReasons] = useState<Reason[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [prisma, setPrisma] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Comment[]>([]);
  const [reviewActions, setReviewActions] = useState<PeerReviewAction[]>([]);
  const [title, setTitle] = useState('Main screening batch');
  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedPaper, setSelectedPaper] = useState('');
  const [decision, setDecision] = useState('include');
  const [reasonLabel, setReasonLabel] = useState('Wrong population');
  const [commentBody, setCommentBody] = useState('');
  const [reviewAction, setReviewAction] = useState('draft_review');
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!projectId) return;
    const [batchResponse, reasonResponse, paperResponse, prismaResponse, commentResponse, reviewResponse] = await Promise.all([
      api.get('/screening/batches', { params: { project_id: projectId } }),
      api.get('/screening/reasons', { params: { project_id: projectId } }),
      api.get(`/projects/${projectId}/library`, { params: { limit: 100 } }),
      api.get('/screening/prisma', { params: { project_id: projectId } }).catch(() => ({ data: { counts: {} } })),
      api.get('/screening/comments', { params: { project_id: projectId } }),
      api.get('/screening/peer-review-actions', { params: { project_id: projectId } }),
    ]);
    const nextBatches = batchResponse.data as Batch[];
    const paperPage = paperResponse.data as PaginatedResponse<Paper>;
    setBatches(nextBatches);
    setReasons(reasonResponse.data as Reason[]);
    setPapers(paperPage.items || []);
    setPrisma((prismaResponse.data?.counts || {}) as Record<string, number>);
    setComments(commentResponse.data as Comment[]);
    setReviewActions(reviewResponse.data as PeerReviewAction[]);
    if (!selectedBatch && nextBatches[0]) setSelectedBatch(nextBatches[0].id);
    if (!selectedPaper && (paperPage.items || [])[0]) setSelectedPaper((paperPage.items || [])[0].id);
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load screening workspace'));
  }, [projectId]);

  async function createBatch() {
    if (!projectId) return;
    try {
      await api.post('/screening/batches', { project_id: projectId, title, stage: 'title_abstract' });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create screening batch');
    }
  }

  async function createReason() {
    if (!projectId) return;
    try {
      await api.post('/screening/reasons', { project_id: projectId, code: reasonLabel.toLowerCase().replace(/\s+/g, '_'), label: reasonLabel });
      setReasonLabel('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create reason');
    }
  }

  async function saveDecision() {
    if (!selectedBatch || !selectedPaper) return;
    try {
      await api.post('/screening/decisions', {
        batch_id: selectedBatch,
        paper_id: selectedPaper,
        decision,
        stage: 'title_abstract',
        reason_id: decision === 'exclude' ? reasons[0]?.id || null : null,
      });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save screening decision');
    }
  }

  async function saveComment() {
    if (!projectId || !commentBody.trim()) return;
    try {
      await api.post('/screening/comments', {
        project_id: projectId,
        body: commentBody.trim(),
        target_type: selectedBatch ? 'screening_batch' : 'project',
        target_id: selectedBatch || projectId,
      });
      setCommentBody('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save comment');
    }
  }

  async function createReviewAction() {
    if (!projectId) return;
    try {
      await api.post('/screening/peer-review-actions', {
        project_id: projectId,
        action: reviewAction,
        status: 'open',
        payload_json: { batch_id: selectedBatch || null, paper_id: selectedPaper || null },
      });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create review action');
    }
  }

  async function resolveReviewAction(actionId: string) {
    try {
      await api.patch(`/screening/peer-review-actions/${actionId}`, { status: 'resolved' });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to resolve review action');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Screening</h1>
        <div className="rc-subtitle">Title/abstract and full-text screening with auditable reasons and lightweight PRISMA counts.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Setup</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch title</div>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={createBatch}>Create batch</button>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Exclusion reason</div>
            <input className="rc-input" value={reasonLabel} onChange={(e) => setReasonLabel(e.target.value)} />
          </div>
          <button className="rc-btn" onClick={createReason}>Add reason</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Decision</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch</div>
            <select className="rc-input" value={selectedBatch} onChange={(e) => setSelectedBatch(e.target.value)}>
              <option value="">Select batch</option>
              {batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.title} · {batch.stage}
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 240 }}>
            <div className="rc-kicker">Paper</div>
            <select className="rc-input" value={selectedPaper} onChange={(e) => setSelectedPaper(e.target.value)}>
              <option value="">Select paper</option>
              {papers.map((paper) => (
                <option key={paper.id} value={paper.id}>{paper.title}</option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 160 }}>
            <div className="rc-kicker">Decision</div>
            <select className="rc-input" value={decision} onChange={(e) => setDecision(e.target.value)}>
              <option value="include">Include</option>
              <option value="exclude">Exclude</option>
              <option value="maybe">Maybe</option>
            </select>
          </div>
          <button className="rc-btn rc-btn--primary" onClick={saveDecision}>Save decision</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Batches</div>
          {batches.length === 0 ? <div className="rc-muted">No screening batches yet.</div> : null}
          {batches.map((batch) => (
            <div key={batch.id} className="rc-help">{batch.title} · {batch.stage} · {batch.status}</div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">PRISMA counts</div>
          {Object.keys(prisma).length === 0 ? <div className="rc-muted">No counts yet.</div> : null}
          {Object.entries(prisma).map(([key, value]) => (
            <div key={key} className="rc-help">{key}: {value}</div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Comments</div>
          <textarea
            className="rc-input"
            style={{ minHeight: 100, width: '100%' }}
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            placeholder="Add a screening or review note…"
          />
          <div style={{ height: 10 }} />
          <button className="rc-btn" onClick={saveComment}>Add comment</button>
          <div style={{ height: 10 }} />
          {comments.length === 0 ? <div className="rc-muted">No comments yet.</div> : null}
          {comments.map((comment) => (
            <div key={comment.id} className="rc-help">
              {comment.body} · {comment.target_type || 'project'} · {comment.user_id}
            </div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Peer review queue</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Action</div>
              <select className="rc-input" value={reviewAction} onChange={(e) => setReviewAction(e.target.value)}>
                <option value="draft_review">Draft review</option>
                <option value="extraction_review">Extraction review</option>
                <option value="screening_review">Screening review</option>
              </select>
            </div>
            <button className="rc-btn" onClick={createReviewAction}>Queue review action</button>
          </div>
          <div style={{ height: 10 }} />
          {reviewActions.length === 0 ? <div className="rc-muted">No peer review actions yet.</div> : null}
          {reviewActions.map((action) => (
            <div key={action.id} className="rc-card" style={{ padding: 12, marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{action.action}</div>
              <div className="rc-help">{action.status} · {action.user_id}</div>
              <div className="rc-row">
                {action.status !== 'resolved' ? (
                  <button className="rc-btn" onClick={() => resolveReviewAction(action.id)}>Resolve</button>
                ) : (
                  <span className="rc-help">Resolved</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

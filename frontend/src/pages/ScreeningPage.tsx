import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

type Batch = { id: string; title: string; stage: string; status: string };
type Reason = { id: string; code: string; label: string };
type Paper = { id: string; title: string };
type Comment = { id: string; user_id: string; body: string; target_type?: string | null; target_id?: string | null };
type PeerReviewAction = { id: string; user_id: string; action: string; status: string; payload_json?: Record<string, unknown> | null };
type Membership = { user_id: string; role: 'owner' | 'editor' | 'reviewer' | 'viewer' };

type PaginatedResponse<T> = {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
  total_count?: number;
};

export default function ScreeningPage() {
  const { projectId } = useParams();
  const user = useAuthStore((state) => state.user);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [reasons, setReasons] = useState<Reason[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [prisma, setPrisma] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Comment[]>([]);
  const [reviewActions, setReviewActions] = useState<PeerReviewAction[]>([]);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [title, setTitle] = useState('Lote principal de screening');
  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedPaper, setSelectedPaper] = useState('');
  const [decision, setDecision] = useState('include');
  const [reasonLabel, setReasonLabel] = useState('Poblacion incorrecta');
  const [commentBody, setCommentBody] = useState('');
  const [reviewAction, setReviewAction] = useState('draft_review');
  const [error, setError] = useState<string | null>(null);
  const currentRole = memberships.find((membership) => membership.user_id === user?.id)?.role || null;
  const canReview = currentRole === 'owner' || currentRole === 'editor' || currentRole === 'reviewer';
  const canEditConfiguration = currentRole === 'owner' || currentRole === 'editor';

  async function load() {
    if (!projectId) return;
    const [batchResponse, reasonResponse, paperResponse, prismaResponse, commentResponse, reviewResponse, memberResponse] = await Promise.all([
      api.get('/screening/batches', { params: { project_id: projectId } }),
      api.get('/screening/reasons', { params: { project_id: projectId } }),
      api.get(`/projects/${projectId}/library`, { params: { limit: 100 } }),
      api.get('/screening/prisma', { params: { project_id: projectId } }).catch(() => ({ data: { counts: {} } })),
      api.get('/screening/comments', { params: { project_id: projectId } }),
      api.get('/screening/peer-review-actions', { params: { project_id: projectId } }),
      api.get(`/projects/${projectId}/members`),
    ]);
    const nextBatches = batchResponse.data as Batch[];
    const paperPage = paperResponse.data as PaginatedResponse<Paper>;
    setBatches(nextBatches);
    setReasons(reasonResponse.data as Reason[]);
    setPapers(paperPage.items || []);
    setPrisma((prismaResponse.data?.counts || {}) as Record<string, number>);
    setComments(commentResponse.data as Comment[]);
    setReviewActions(reviewResponse.data as PeerReviewAction[]);
    setMemberships(memberResponse.data as Membership[]);
    if (!selectedBatch && nextBatches[0]) setSelectedBatch(nextBatches[0].id);
    if (!selectedPaper && (paperPage.items || [])[0]) setSelectedPaper((paperPage.items || [])[0].id);
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'No se pudo cargar el espacio de screening'));
  }, [projectId]);

  async function createBatch() {
    if (!projectId || !canEditConfiguration) return;
    try {
      await api.post('/screening/batches', { project_id: projectId, title, stage: 'title_abstract' });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el lote de screening');
    }
  }

  async function createReason() {
    if (!projectId || !canEditConfiguration) return;
    try {
      await api.post('/screening/reasons', { project_id: projectId, code: reasonLabel.toLowerCase().replace(/\s+/g, '_'), label: reasonLabel });
      setReasonLabel('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el motivo');
    }
  }

  async function saveDecision() {
    if (!selectedBatch || !selectedPaper || !canReview) return;
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
      setError(e?.response?.data?.detail || 'No se pudo guardar la decision');
    }
  }

  async function saveComment() {
    if (!projectId || !commentBody.trim() || !canReview) return;
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
      setError(e?.response?.data?.detail || 'No se pudo guardar el comentario');
    }
  }

  async function createReviewAction() {
    if (!projectId || !canReview) return;
    try {
      await api.post('/screening/peer-review-actions', {
        project_id: projectId,
        action: reviewAction,
        status: 'open',
        payload_json: { batch_id: selectedBatch || null, paper_id: selectedPaper || null },
      });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear la accion de revision');
    }
  }

  async function resolveReviewAction(actionId: string) {
    if (!canReview) return;
    try {
      await api.patch(`/screening/peer-review-actions/${actionId}`, { status: 'resolved' });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo resolver la accion de revision');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Cribado</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Revision de elegibilidad</h1>
          <div className="rc-subtitle">Cribado por titulo/resumen y texto completo con motivos auditables y conteos PRISMA ligeros.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{batches.length}</strong><span>Lotes</span></div>
          <div className="rc-metric-tile"><strong>{comments.length}</strong><span>Comentarios</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {currentRole ? (
        <div className="rc-help">
          Tu rol actual es <b>{currentRole}</b>. {!canEditConfiguration ? 'La configuracion del screening es de solo lectura para este rol.' : 'Puedes configurar lotes y motivos de exclusion.'}
        </div>
      ) : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-card">
          <div className="rc-card-title">Configuracion</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Titulo del lote</div>
              <input data-testid="screening-batch-title-input" className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
            <button data-testid="screening-create-batch" className="rc-btn" onClick={createBatch} disabled={!canEditConfiguration}>Crear lote</button>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Motivo de exclusion</div>
              <input data-testid="screening-reason-input" className="rc-input" value={reasonLabel} onChange={(e) => setReasonLabel(e.target.value)} />
            </div>
            <button data-testid="screening-add-reason" className="rc-btn" onClick={createReason} disabled={!canEditConfiguration}>Agregar motivo</button>
          </div>
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Decision</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Lote</div>
              <select data-testid="screening-batch-select" className="rc-input" value={selectedBatch} onChange={(e) => setSelectedBatch(e.target.value)}>
                <option value="">Seleccionar lote</option>
                {batches.map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    {batch.title} · {batch.stage}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ minWidth: 240 }}>
              <div className="rc-kicker">Paper</div>
              <select data-testid="screening-paper-select" className="rc-input" value={selectedPaper} onChange={(e) => setSelectedPaper(e.target.value)}>
                <option value="">Seleccionar paper</option>
                {papers.map((paper) => (
                  <option key={paper.id} value={paper.id}>{paper.title}</option>
                ))}
              </select>
            </div>
            <div style={{ minWidth: 160 }}>
              <div className="rc-kicker">Decision</div>
              <select data-testid="screening-decision-select" className="rc-input" value={decision} onChange={(e) => setDecision(e.target.value)}>
                <option value="include">Incluir</option>
                <option value="exclude">Excluir</option>
                <option value="maybe">Tal vez</option>
              </select>
            </div>
            <button data-testid="screening-save-decision" className="rc-btn rc-btn--primary" onClick={saveDecision} disabled={!canReview}>Guardar decision</button>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Lotes</div>
          {batches.length === 0 ? <div className="rc-muted">Todavia no hay lotes de cribado.</div> : null}
          {batches.map((batch) => (
            <div key={batch.id} className="rc-help">{batch.title} · {batch.stage} · {batch.status}</div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Conteos PRISMA</div>
          {Object.keys(prisma).length === 0 ? <div className="rc-muted">Todavia no hay conteos.</div> : null}
          {Object.entries(prisma).map(([key, value]) => (
            <div key={key} className="rc-help">{key}: {value}</div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Comentarios</div>
          <textarea
            data-testid="screening-comment-input"
            className="rc-input"
            style={{ minHeight: 100, width: '100%' }}
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            placeholder="Agrega una nota de screening o revision…"
          />
          <div style={{ height: 10 }} />
          <button data-testid="screening-add-comment" className="rc-btn" onClick={saveComment} disabled={!canReview}>Agregar comentario</button>
          <div style={{ height: 10 }} />
          {comments.length === 0 ? <div className="rc-muted">Todavia no hay comentarios.</div> : null}
          {comments.map((comment) => (
            <div key={comment.id} className="rc-help">
              {comment.body} · {comment.target_type || 'project'} · {comment.user_id}
            </div>
          ))}
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Cola de revision por pares</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Accion</div>
              <select data-testid="screening-review-action-select" className="rc-input" value={reviewAction} onChange={(e) => setReviewAction(e.target.value)}>
                <option value="draft_review">Revision de borrador</option>
                <option value="extraction_review">Revision de extraccion</option>
                <option value="screening_review">Revision de screening</option>
              </select>
            </div>
            <button data-testid="screening-queue-review-action" className="rc-btn" onClick={createReviewAction} disabled={!canReview}>Encolar accion de revision</button>
          </div>
          <div style={{ height: 10 }} />
          {reviewActions.length === 0 ? <div className="rc-muted">Todavia no hay acciones de revision.</div> : null}
          {reviewActions.map((action) => (
            <div key={action.id} className="rc-soft-card" style={{ marginBottom: 10 }}>
              <div style={{ fontWeight: 800 }}>{action.action}</div>
              <div className="rc-help">{action.status} · {action.user_id}</div>
              <div className="rc-row">
                {action.status !== 'resolved' ? (
                  <button data-testid={`screening-resolve-review-${action.id}`} className="rc-btn" onClick={() => resolveReviewAction(action.id)} disabled={!canReview}>Resolver</button>
                ) : (
                  <span className="rc-help">Resuelta</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';
import type { MembershipRole, ProjectMember } from '../types/api';

type Batch = { id: string; title: string; stage: string; status: string };
type Reason = { id: string; code: string; label: string };
type Paper = { id: string; title: string };

// M9: PRISMA diagram rendered via mermaid
function PrismaFlowDiagram({ counts }: { counts: Record<string, number> }) {
  const [svgHtml, setSvgHtml] = useState<string>('');

  useEffect(() => {
    if (Object.keys(counts).length === 0) return;
    const identified = counts.identified ?? counts.total ?? 0;
    const screened = counts.screened ?? counts.title_abstract ?? 0;
    const eligible = counts.eligible ?? counts.full_text ?? 0;
    const included = counts.included ?? 0;
    const excluded = identified - screened;
    const notEligible = screened - eligible;
    const excludedFullText = eligible - included;

    const diagram = `flowchart TD
    A["📚 Records identified<br/><b>${identified}</b>"] --> B["🔍 Records screened<br/><b>${screened}</b>"]
    A --> A1["❌ Records excluded<br/>(deduplication)<br/><b>${excluded < 0 ? 0 : excluded}</b>"]
    B --> C["📄 Full-text assessed<br/>for eligibility<br/><b>${eligible}</b>"]
    B --> B1["❌ Records excluded<br/><b>${notEligible < 0 ? 0 : notEligible}</b>"]
    C --> D["✅ Studies included<br/>in synthesis<br/><b>${included}</b>"]
    C --> C1["❌ Full-text excluded<br/><b>${excludedFullText < 0 ? 0 : excludedFullText}</b>"]
    style D fill:#dcfce7,stroke:#16a34a,color:#166534
    style A fill:#dbeafe,stroke:#2563eb,color:#1e40af
    style B fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
    style C fill:#fef3c7,stroke:#d97706,color:#92400e`;

    import('mermaid').then(mod => {
      const mermaid = mod.default;
      mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'strict' });
      const id = `prisma-${Date.now()}`;
      mermaid.render(id, diagram).then(({ svg }) => {
        setSvgHtml(svg);
      }).catch(() => {});
    }).catch(() => {});
  }, [counts]);

  if (Object.keys(counts).length === 0) return null;

  return (
    <div>
      <div className="rc-card-title" style={{ marginBottom: 12 }}>PRISMA Flow Diagram</div>
      <div dangerouslySetInnerHTML={{ __html: svgHtml }} style={{ minHeight: 200, display: 'flex', justifyContent: 'center' }} />
    </div>
  );
}

export default function ScreeningPage() {
  const { projectId } = useParams();
  const user = useAuthStore((state) => state.user);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [reasons, setReasons] = useState<Reason[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [prisma, setPrisma] = useState<Record<string, number>>({});
  const [projectRole, setProjectRole] = useState<MembershipRole | null>(null);
  const [title, setTitle] = useState('Main screening batch');
  const [selectedBatch, setSelectedBatch] = useState('');
  const [selectedPaper, setSelectedPaper] = useState('');
  const [decision, setDecision] = useState('include');
  const [reasonLabel, setReasonLabel] = useState('Wrong population');
  const [commentBody, setCommentBody] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const canManageScreening = projectRole === 'owner' || projectRole === 'editor';
  const canComment = projectRole === 'owner' || projectRole === 'editor' || projectRole === 'viewer';

  const load = useCallback(async () => {
    if (!projectId) return;
    const [batchResponse, reasonResponse, paperResponse, prismaResponse, membersResponse] = await Promise.all([
      api.get('/screening/batches', { params: { project_id: projectId } }),
      api.get('/screening/reasons', { params: { project_id: projectId } }),
      api.get(`/projects/${projectId}/library`),
      api.get('/screening/prisma', { params: { project_id: projectId } }).catch(() => ({ data: { counts: {} } })),
      api.get(`/projects/${projectId}/members`).catch(() => ({ data: [] })),
    ]);
    const nextBatches = batchResponse.data as Batch[];
    const nextPapers = paperResponse.data as Paper[];
    const members = membersResponse.data as ProjectMember[];
    setBatches(nextBatches);
    setReasons(reasonResponse.data as Reason[]);
    setPapers(nextPapers);
    setPrisma((prismaResponse.data?.counts || {}) as Record<string, number>);
    setProjectRole(members.find((member) => member.user_id === user?.id)?.role || null);
    if (!selectedBatch && nextBatches[0]) setSelectedBatch(nextBatches[0].id);
    if (!selectedPaper && nextPapers[0]) setSelectedPaper(nextPapers[0].id);
  }, [projectId, selectedBatch, selectedPaper, user?.id]);

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load screening workspace'));
  }, [load]);

  async function createBatch() {
    if (!projectId || !canManageScreening) return;
    try {
      setError(null);
      setNotice(null);
      await api.post('/screening/batches', { project_id: projectId, title, stage: 'title_abstract' });
      setNotice('Screening batch created.');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create screening batch');
    }
  }

  async function createReason() {
    if (!projectId || !canManageScreening) return;
    try {
      setError(null);
      setNotice(null);
      await api.post('/screening/reasons', { project_id: projectId, code: reasonLabel.toLowerCase().replace(/\s+/g, '_'), label: reasonLabel });
      setReasonLabel('');
      setNotice('Exclusion reason added.');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create reason');
    }
  }

  async function saveDecision() {
    if (!canManageScreening || !selectedBatch || !selectedPaper) return;
    try {
      setError(null);
      setNotice(null);
      await api.post('/screening/decisions', {
        batch_id: selectedBatch,
        paper_id: selectedPaper,
        decision,
        stage: 'title_abstract',
        reason_id: decision === 'exclude' ? reasons[0]?.id || null : null,
      });
      setNotice('Screening decision saved.');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save screening decision');
    }
  }

  async function addComment() {
    if (!projectId || !selectedPaper || !canComment) return;
    if (!commentBody.trim()) {
      setError('Write a comment before adding it to the screening workflow.');
      return;
    }
    try {
      setError(null);
      setNotice(null);
      await api.post('/screening/comments', {
        project_id: projectId,
        body: commentBody.trim(),
        target_type: 'paper',
        target_id: selectedPaper,
      });
      setCommentBody('');
      setNotice('Comment added to the screening workflow.');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add comment');
    }
  }

  async function queueReviewAction() {
    if (!projectId || !selectedPaper || !canComment) return;
    try {
      setError(null);
      setNotice(null);
      await api.post('/screening/peer-review-actions', {
        project_id: projectId,
        action: 'screening_review',
        status: 'open',
        payload_json: {
          paper_id: selectedPaper,
          batch_id: selectedBatch || null,
          stage: 'title_abstract',
        },
      });
      setNotice('Peer review action queued.');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to queue peer review');
    }
  }

  return (
    <div className="rc-page-enter" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Screening</h1>
        <div className="rc-subtitle">Title/abstract and full-text screening with auditable reasons and lightweight PRISMA counts.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Setup</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Batch title</div>
            <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <button
            className="rc-btn"
            data-testid="screening-create-batch"
            disabled={!canManageScreening || !title.trim()}
            onClick={createBatch}
          >
            Create batch
          </button>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Exclusion reason</div>
            <input className="rc-input" value={reasonLabel} onChange={(e) => setReasonLabel(e.target.value)} />
          </div>
          <button className="rc-btn" disabled={!canManageScreening || !reasonLabel.trim()} onClick={createReason}>Add reason</button>
        </div>
        <div className="rc-help" style={{ marginTop: 10 }}>
          {canManageScreening
            ? 'Editors and owners can create batches, define reasons and save screening decisions.'
            : 'Viewers can comment and queue peer review requests, but only editors or owners can change screening structure.'}
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
          <button className="rc-btn rc-btn--primary" disabled={!canManageScreening || !selectedBatch || !selectedPaper} onClick={saveDecision}>Save decision</button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Collaboration actions</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 280, flex: 1 }}>
            <div className="rc-kicker">Comment for the current paper</div>
            <input
              className="rc-input"
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              placeholder="Leave a note for the screening team"
            />
          </div>
          <button
            className="rc-btn"
            data-testid="screening-add-comment"
            disabled={!canComment || !selectedPaper}
            onClick={addComment}
          >
            Add comment
          </button>
          <button
            className="rc-btn rc-btn--primary"
            data-testid="screening-queue-review-action"
            disabled={!canComment || !selectedPaper}
            onClick={queueReviewAction}
          >
            Queue review action
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div className="rc-card">
          <div className="rc-card-title">Batches</div>
          {batches.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px' }}>
              <svg width="56" height="56" viewBox="0 0 56 56" fill="none" style={{ margin: '0 auto 10px', display: 'block' }}>
                <rect x="6" y="8" width="44" height="32" rx="4" fill="rgba(16,185,129,0.07)" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5"/>
                <line x1="14" y1="18" x2="38" y2="18" stroke="rgba(16,185,129,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
                <line x1="14" y1="24" x2="38" y2="24" stroke="rgba(16,185,129,0.2)" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="42" cy="42" r="12" fill="var(--rc-surface)" stroke="rgba(16,185,129,0.3)" strokeWidth="1.5"/>
                <path d="M38 42h8M42 38v8" stroke="rgba(16,185,129,0.65)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--rc-text)' }}>No screening batches yet</div>
              <div style={{ fontSize: 12, color: 'var(--rc-muted)', marginTop: 3 }}>Create a batch to start screening papers</div>
            </div>
          ) : null}
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
          {Object.keys(prisma).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <PrismaFlowDiagram counts={prisma} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

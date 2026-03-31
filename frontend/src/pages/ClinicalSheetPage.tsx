import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ClinicalProViewer from '../components/clinical/ClinicalProViewer';
import EvidenceDrawer from '../domain/clinical/components/EvidenceDrawer';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import { useClinicalSheet } from '../domain/clinical/hooks/useClinicalSheet';
import { enqueueClinicalUpdate } from '../services/clinical';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { Breadcrumb } from '../components/Breadcrumb';

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

function slugify(s: string) {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s\-áéíóúüñ]/gi, '')
    .replace(/\s+/g, '-')
    .slice(0, 80);
}

export default function ClinicalSheetPage() {
  const { sheetId } = useParams();
  const [searchParams] = useSearchParams();
  const fromProject = searchParams.get('from_project');
  const toast = useToast();
  const confirm = useConfirm();

  const vm = useClinicalSheet(sheetId);

  const [notice, setNotice] = useState<string | null>(null);
  const [outlineOpen, setOutlineOpen] = useState(true);
  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const workspaceColumns = `${outlineOpen ? '280px ' : ''}minmax(0,1fr)${evidenceOpen ? ' 340px' : ''}`;

  async function doUpdate() {
    if (!sheetId) return;
    const ok = await confirm({
      title: 'Update this clinical sheet?',
      body: 'This will enqueue a background job to regenerate content using the current pipeline. Existing versions remain available.',
      confirmText: 'Update',
    });
    if (!ok) return;

    try {
      const r = await enqueueClinicalUpdate(sheetId);
      setNotice(`Update enqueued: job ${r.job_id}`);
      toast.success('Job enqueued', 'Clinical sheet update started.');
    } catch (e: any) {
      toast.error('Update failed', e?.response?.data?.detail || e?.message || 'Update failed');
    }
  }

  async function exportDocx() {
    if (!sheetId) return;
    try {
      const { api } = await import('../services/api');
      const r = await api.get(`/clinical/${sheetId}/download?format=docx`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, `clinical_${sheetId}.docx`);
      toast.success('Download started', 'DOCX export');
    } catch (e: any) {
      toast.error('Export failed', e?.response?.data?.detail || 'Export DOCX failed');
    }
  }

  async function exportPdf() {
    if (!sheetId) return;
    try {
      const { api } = await import('../services/api');
      const r = await api.get(`/clinical/${sheetId}/download?format=pdf`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, `clinical_${sheetId}.pdf`);
      toast.success('Download started', 'PDF export');
    } catch (e: any) {
      toast.error('Export failed', e?.response?.data?.detail || 'Export PDF failed');
    }
  }

  async function useForPresentation() {
    try {
      const sheet = vm.sheet;
      const papers = (sheet?.sources_used || {})?.papers || [];
      const paperIds = (papers || []).map((p: any) => p.paper_id).filter(Boolean);
      const projectId = sheet?.project_id;
      if (!projectId) throw new Error('This sheet is not linked to a project.');
      if (!paperIds.length) throw new Error('No project papers linked; cannot generate presentation.');

      const ok = await confirm({
        title: 'Create a presentation deck from this sheet?',
        body: 'We will use the linked project papers to generate a non-generic, citation-backed PPTX deck.',
        confirmText: 'Create deck',
      });
      if (!ok) return;

      const { api } = await import('../services/api');
      const r = await api.post('/presentations/generate', {
        project_id: projectId,
        topic: sheet?.topic || 'Clinical sheet',
        duration_minutes: 45,
        audience: 'universidad',
        paper_ids: paperIds,
        num_slides: 36,
      });

      setNotice(`Presentation job enqueued: ${r.data?.job_id}`);
      toast.success('Job enqueued', 'Presentation deck generation started.');
    } catch (e: any) {
      toast.error('Deck generation failed', e?.message || e?.response?.data?.detail || 'Use for presentation failed');
    }
  }

  if (!sheetId) return <div className="rc-muted">Missing sheet id</div>;

  if (vm.status === 'loading' && !vm.sheet) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: workspaceColumns, gap: 12, alignItems: 'start' }}>
        {outlineOpen ? <aside className="rc-card" style={{ position: 'sticky', top: 12, height: 'fit-content' }}>
          <div className="rc-card-title">Outline</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Skeleton height={12} width="85%" />
            <Skeleton height={12} width="70%" />
            <Skeleton height={12} width="92%" />
            <Skeleton height={12} width="64%" />
            <Skeleton height={12} width="78%" />
          </div>
        </aside> : null}

        <main>
          <div className="rc-card" style={{ position: 'sticky', top: 12, zIndex: 5 }}>
            <Skeleton height={18} width="55%" />
            <div style={{ height: 8 }} />
            <Skeleton height={12} width="35%" />
            <div style={{ height: 10 }} />
            <div className="rc-row" style={{ flexWrap: 'wrap' }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} height={34} width={110} radius={12} />
              ))}
            </div>
          </div>

          <div style={{ height: 12 }} />

          <div className="rc-card">
            <SkeletonLines lines={10} lineHeight={12} />
            <div style={{ height: 14 }} />
            <SkeletonLines lines={10} lineHeight={12} lastLineWidth="45%" />
          </div>
        </main>

        {evidenceOpen ? <aside style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 12, height: 'fit-content' }}>
          <div className="rc-card">
            <div className="rc-card-title">Versions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <Skeleton height={46} radius={12} />
              <Skeleton height={46} radius={12} />
              <Skeleton height={46} radius={12} />
            </div>
          </div>

          <div className="rc-card">
            <div className="rc-card-title">Evidence</div>
            <SkeletonLines lines={6} lineHeight={12} lastLineWidth="55%" />
          </div>
        </aside> : null}
      </div>
    );
  }

  // Breadcrumb: prioritise project context, fall back to clinical list
  const projectId = fromProject || vm.sheet?.project_id;
  const breadcrumbItems = projectId
    ? [
        { label: 'Projects', to: '/projects' },
        { label: 'Project', to: `/projects/${projectId}/research` },
        { label: 'Clinical Sheet' },
      ]
    : [
        { label: 'Clinical', to: '/clinical' },
        { label: vm.sheet?.topic || 'Sheet' },
      ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Breadcrumb items={breadcrumbItems} />
    <div style={{ display: 'grid', gridTemplateColumns: workspaceColumns, gap: 12, alignItems: 'start' }}>
      {outlineOpen ? <aside className="rc-card" style={{ position: 'sticky', top: 12, height: 'fit-content' }}>
        <div className="rc-card-title">Outline</div>
        {vm.toc.length === 0 ? <div className="rc-muted">No headings.</div> : null}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {vm.toc.map((t) => (
            <a key={t.id} href={`#${t.id}`} className="rc-help" style={{ textDecoration: 'none', color: 'inherit' }}>
              {t.text}
            </a>
          ))}
        </div>
        <div style={{ height: 10 }} />
        <div className="rc-help">Tip: use the outline to jump between sections.</div>
      </aside> : null}

      <main>
        <div className="rc-card" style={{ position: 'sticky', top: 12, zIndex: 5 }}>
          {vm.error ? <div className="rc-error">{String(vm.error)}</div> : null}
          {notice ? (
            <div className="rc-badge rc-badge--success" style={{ justifyContent: 'flex-start', borderRadius: 12, padding: 10 }}>
              {notice}
            </div>
          ) : null}

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 260, flex: 1 }}>
              <div style={{ fontWeight: 950, fontSize: 18, letterSpacing: '-0.02em' }}>{vm.sheet?.topic || 'Clinical sheet'}</div>
              <div className="rc-help" style={{ marginTop: 4 }}>
                v{vm.sheet?.version} {vm.sheet?.is_current ? '· current' : ''}
                {vm.sheet?.format_version ? ` · ${vm.sheet.format_version}` : ''}
              </div>
            </div>

            <div className="rc-row">
              <button className="rc-btn" onClick={() => setOutlineOpen((value) => !value)}>
                {outlineOpen ? 'Hide outline' : 'Show outline'}
              </button>
              <button className="rc-btn" onClick={() => setEvidenceOpen((value) => !value)}>
                {evidenceOpen ? 'Hide evidence rail' : 'Show evidence rail'}
              </button>
              <button className="rc-btn" onClick={vm.refresh} disabled={vm.status === 'loading'}>
                {vm.status === 'loading' ? 'Refreshing…' : 'Refresh'}
              </button>
              <button className="rc-btn" onClick={doUpdate}>Update sheet</button>
              <button className="rc-btn" onClick={exportDocx}>Download DOCX</button>
              <button className="rc-btn" onClick={exportPdf}>Download PDF</button>
              <button className="rc-btn rc-btn--primary" onClick={useForPresentation}>Create deck</button>
            </div>
          </div>
        </div>

        <div style={{ height: 12 }} />

        <div className="rc-card">
          {vm.sheet?.format_version === 'clinical_pro_v1' && vm.sheet?.content_json ? (
            <ClinicalProViewer pro={vm.sheet.content_json} />
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h2: ({ children }) => {
                  const text = String(children || '').trim();
                  const id = slugify(text);
                  return (
                    <h2 id={id} style={{ marginTop: 18 }}>
                      {children}
                    </h2>
                  );
                },
                table: ({ children }) => (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ borderCollapse: 'collapse', width: '100%' }}>{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, background: 'rgba(0,0,0,0.04)', textAlign: 'left' }}>{children}</th>
                ),
                td: ({ children }) => <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6 }}>{children}</td>,
              }}
            >
              {vm.sheet?.content_markdown || ''}
            </ReactMarkdown>
          )}
        </div>
      </main>

      {evidenceOpen ? <aside style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 12, height: 'fit-content' }}>
        <div className="rc-card">
          <div className="rc-card-title">Versions</div>
          {vm.versions.length === 0 ? <div className="rc-muted">No versions.</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {vm.versions.map((v) => (
              <button
                key={v.id}
                onClick={() => vm.openVersion(v.id)}
                className="rc-btn"
                style={{
                  textAlign: 'left',
                  padding: 12,
                  borderColor: v.id === sheetId ? 'rgba(79,70,229,0.35)' : 'rgba(15,23,42,0.16)',
                  background: v.id === sheetId ? 'rgba(79,70,229,0.08)' : 'white',
                }}
              >
                <div style={{ fontWeight: 850 }}>
                  v{v.version} {v.is_current ? '· current' : ''}
                </div>
                {v.created_at ? <div className="rc-help">{v.created_at}</div> : null}
              </button>
            ))}
          </div>
        </div>

        <EvidenceDrawer summary={vm.evidenceSummary} />

        {/* ── Papers used from project ── */}
        {(() => {
          const projectPapers: Array<{ paper_id?: string; doi?: string; pmid?: string }> =
            (vm.sheet?.sources_used as any)?.papers || [];
          if (!projectPapers.length) return null;
          return (
            <div className="rc-card">
              <div className="rc-card-title" style={{ marginBottom: 8 }}>
                📄 Project papers used
              </div>
              <div style={{ fontSize: 12, color: 'var(--rc-muted)', marginBottom: 8 }}>
                {projectPapers.length} paper{projectPapers.length !== 1 ? 's' : ''} from this project contributed evidence to this sheet.
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {projectPapers.map((p, i) => (
                  <div key={p.paper_id || i} style={{ fontSize: 12, padding: '6px 8px', borderRadius: 6, background: 'var(--rc-bg-secondary, rgba(0,0,0,0.03))', border: '1px solid var(--rc-border)' }}>
                    {p.doi && (
                      <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer" style={{ color: 'var(--rc-accent, #6366f1)', fontWeight: 600 }}>
                        DOI: {p.doi}
                      </a>
                    )}
                    {!p.doi && p.pmid && (
                      <a href={`https://pubmed.ncbi.nlm.nih.gov/${p.pmid}`} target="_blank" rel="noreferrer" style={{ color: 'var(--rc-accent, #6366f1)', fontWeight: 600 }}>
                        PMID: {p.pmid}
                      </a>
                    )}
                    {!p.doi && !p.pmid && (
                      <span style={{ color: 'var(--rc-muted)', fontFamily: 'monospace' }}>
                        {p.paper_id?.slice(0, 8)}…
                      </span>
                    )}
                  </div>
                ))}
              </div>
              {vm.sheet?.project_id && (
                <div style={{ marginTop: 10 }}>
                  <a
                    href={`/projects/${vm.sheet.project_id}/library`}
                    style={{ fontSize: 12, color: 'var(--rc-accent, #6366f1)', fontWeight: 600 }}
                  >
                    → View project library
                  </a>
                </div>
              )}
            </div>
          );
        })()}
      </aside> : null}
    </div>
    </div>
  );
}

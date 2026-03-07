import { useState } from 'react';
import { useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ClinicalProViewer from '../components/clinical/ClinicalProViewer';
import EvidenceDrawer from '../domain/clinical/components/EvidenceDrawer';
import { api } from '../services/api';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';
import { useClinicalSheet } from '../domain/clinical/hooks/useClinicalSheet';
import { enqueueClinicalUpdate } from '../services/clinical';
import { useToast } from '../ui/Toast/ToastProvider';
import { useConfirm } from '../ui/Dialog/useConfirm';

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
  const toast = useToast();
  const confirm = useConfirm();

  const vm = useClinicalSheet(sheetId);

  const [notice, setNotice] = useState<string | null>(null);

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
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 360px', gap: 12, alignItems: 'start' }}>
        <aside className="rc-card" style={{ position: 'sticky', top: 12, height: 'fit-content' }}>
          <div className="rc-card-title">Outline</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Skeleton height={12} width="85%" />
            <Skeleton height={12} width="70%" />
            <Skeleton height={12} width="92%" />
            <Skeleton height={12} width="64%" />
            <Skeleton height={12} width="78%" />
          </div>
        </aside>

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

        <aside style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 12, height: 'fit-content' }}>
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
        </aside>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 360px', gap: 12, alignItems: 'start' }}>
      <aside className="rc-card" style={{ position: 'sticky', top: 12, height: 'fit-content' }}>
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
      </aside>

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

      <aside style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 12, height: 'fit-content' }}>
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
      </aside>
    </div>
  );
}

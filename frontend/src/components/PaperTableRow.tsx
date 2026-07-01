import { memo, Fragment } from 'react';
import type { PaperRow, PaperDownloadTrace } from '../types/api';

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  europepmc: 'Europe PMC',
  doaj: 'DOAJ',
  unpaywall: 'Unpaywall',
  doi_content_negotiation: 'DOI direct',
  manual_upload: 'Carga manual',
  user_provided_oa: 'OA provista',
};

function truncate(s: string, max: number) { return s.length > max ? s.slice(0, max) + '…' : s; }

function providerLabel(source?: string | null) {
  return SOURCE_LABELS[String(source || '').toLowerCase()] || 'Fuente externa';
}

function traceStatusLabel(status: PaperDownloadTrace['final_status']) {
  if (status === 'downloaded') return 'Descargado';
  if (status === 'existing') return 'Ya existía';
  if (status === 'unavailable') return 'No disponible';
  return 'Fallido';
}

function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusTag(status?: string) {
  const s = (status || 'uploaded').toLowerCase();
  if (s === 'ready' || s === 'parsed') return { cls: 'rc-badge rc-badge--success', label: 'Ready' };
  if (s === 'processing' || s === 'queued') return { cls: 'rc-badge rc-badge--info', label: 'Processing' };
  if (s === 'failed') return { cls: 'rc-badge rc-badge--danger', label: 'Failed' };
  return { cls: 'rc-badge', label: 'Pending' };
}

interface PaperTableRowProps {
  p: PaperRow;
  isSelected: boolean;
  isExpanded: boolean;
  isLoadingTrace: boolean;
  traceError: string | null;
  traceData: PaperDownloadTrace | null | undefined;
  onToggleOne: (id: string) => void;
  onProcessMutate: (id: string) => void;
  onDownloadFile: (p: PaperRow) => void;
  onToggleTrace: (p: PaperRow) => void;
  onFavoriteMutate: (p: PaperRow) => void;
  onDeleteWithConfirm: (p: PaperRow) => void;
}

const PaperTableRow = memo(function PaperTableRow({
  p,
  isSelected,
  isExpanded,
  isLoadingTrace,
  traceError,
  traceData,
  onToggleOne,
  onProcessMutate,
  onDownloadFile,
  onToggleTrace,
  onFavoriteMutate,
  onDeleteWithConfirm,
}: PaperTableRowProps) {
  const st = statusTag(p.processing_status);
  const isReady = ['ready', 'parsed'].includes((p.processing_status || '').toLowerCase());

  return (
    <Fragment>
      <tr style={{ borderBottom: '1px solid var(--rc-border)' }}>
        <td style={{ padding: '8px 6px' }}>
          <input type="checkbox" checked={isSelected} onChange={() => onToggleOne(p.id)} aria-label={`Select ${p.title}`} />
        </td>
        <td style={{ padding: '8px 6px' }}>
          <div title={p.title} style={{ fontWeight: 700, lineHeight: 1.3 }}>{truncate(p.title, 45)}</div>
          {p.authors && <div style={{ fontSize: 11, color: 'var(--rc-muted)', marginTop: 2 }}>{truncate(p.authors, 60)}</div>}
        </td>
        <td style={{ padding: '8px 6px', fontStyle: 'italic', fontSize: 12 }}>
          {[p.journal, p.publication_year].filter(Boolean).join(' · ') || '—'}
        </td>
        <td style={{ padding: '8px 6px' }}>
          <span className={st.cls} style={{ fontSize: 11 }}>
            {st.label === 'Processing' && <span style={{ display: 'inline-block', width: 8, height: 8, border: '2px solid rgba(59,130,246,0.4)', borderTopColor: 'rgba(59,130,246,1)', borderRadius: '50%', animation: 'spin .8s linear infinite', marginRight: 4 }} />}
            {st.label}
          </span>
        </td>
        <td style={{ padding: '8px 6px' }}>
          {p.source_provider ? <span className="rc-badge" style={{ fontSize: 11 }}>{providerLabel(p.source_provider)}</span> : <span className="rc-help">—</span>}
        </td>
        <td style={{ padding: '8px 6px' }}>
          <div className="rc-row" style={{ gap: 4, flexWrap: 'wrap' }}>
            {!isReady && <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => onProcessMutate(p.id)}>Process</button>}
            <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => onDownloadFile(p)}>Download</button>
            <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => onToggleTrace(p)}>
              {isExpanded ? 'Hide trace' : 'Trace'}
            </button>
            <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: p.favorite ? '#eab308' : undefined }} onClick={() => onFavoriteMutate(p)} title={p.favorite ? 'Remove favorite' : 'Favorite'} aria-label={`${p.favorite ? 'Remove' : 'Add'} ${p.title} ${p.favorite ? 'from' : 'to'} favorites`}>
              {p.favorite ? '★' : '☆'}
            </button>
            <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--rc-danger)' }} onClick={() => onDeleteWithConfirm(p)}>Del</button>
          </div>
        </td>
      </tr>
      {isExpanded ? (
        <tr style={{ background: 'var(--rc-surface-2)' }}>
          <td colSpan={6} style={{ padding: 12 }}>
            {isLoadingTrace ? (
              <div className="rc-help">Cargando traza…</div>
            ) : traceError ? (
              <div className="rc-error">{traceError}</div>
            ) : traceData ? (
              <div style={{ display: 'grid', gap: 8 }}>
                <div className="rc-row" style={{ gap: 8, flexWrap: 'wrap' }}>
                  <span className="rc-badge">{traceStatusLabel(traceData.final_status)}</span>
                  <span className="rc-badge">{providerLabel(traceData.source_provider)}</span>
                  {traceData.used_fallback ? <span className="rc-badge">Usó fallback</span> : null}
                </div>
                <div className="rc-help">Auditado: {formatDate(traceData.audited_at)}</div>
                <div className="rc-help">OA URL: {traceData.oa_url ? <a href={traceData.oa_url} target="_blank" rel="noopener noreferrer">{traceData.oa_url}</a> : '—'}</div>
                <div className="rc-help">Landing URL: {traceData.landing_url ? <a href={traceData.landing_url} target="_blank" rel="noopener noreferrer">{traceData.landing_url}</a> : '—'}</div>
                <div className="rc-help">Resolved URL: {traceData.resolved_url ? <a href={traceData.resolved_url} target="_blank" rel="noopener noreferrer">{traceData.resolved_url}</a> : '—'}</div>
                <div className="rc-help">Resultado: {traceData.failure_reason || traceStatusLabel(traceData.final_status)}</div>
              </div>
            ) : (
              <div className="rc-help">Este paper no tiene una auditoría de descarga OA registrada.</div>
            )}
          </td>
        </tr>
      ) : null}
    </Fragment>
  );
});

export default PaperTableRow;

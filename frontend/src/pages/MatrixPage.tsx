import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { downloadBlob } from '../components/meta/exportUtils';

type MatrixVersionListItem = {
  id: string;
  project_id: string;
  version_number: number;
  status: string;
  schema_version: string;
  is_current: boolean;
  summary: Record<string, number>;
  validation_summary: Record<string, number>;
  created_at?: string | null;
};

type MatrixVersionDetail = MatrixVersionListItem & {
  rows: Array<Record<string, unknown>>;
  validation_issues: Array<{
    id: string;
    severity: string;
    code: string;
    message: string;
    field_name: string | null;
    row_id: string | null;
  }>;
};

type ComparisonRow = {
  study_id: string | null;
  paper_id: string | null;
  pmid: string;
  doi: string;
  confidence: number;
  cells: Record<string, string>;
};

type ComparisonView = {
  matrix_version_id: string;
  project_id: string;
  version_number: number;
  columns: Array<{ key: string; label: string }>;
  rows: ComparisonRow[];
  row_count: number;
};

const EXPORT_FORMATS = ['xlsx', 'csv', 'json', 'xml'] as const;

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
}

export default function MatrixPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'detail' | 'comparison'>('detail');

  const versionsQuery = useQuery<MatrixVersionListItem[]>({
    queryKey: ['matrix-versions', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/matrix/versions', { params: { project_id: projectId } });
      return response.data as MatrixVersionListItem[];
    },
  });

  const selectedVersionFromList = useMemo(() => {
    if (!versionsQuery.data || versionsQuery.data.length === 0) return null;
    if (selectedVersionId) return versionsQuery.data.find((item) => item.id === selectedVersionId) || null;
    return versionsQuery.data[0];
  }, [versionsQuery.data, selectedVersionId]);

  const detailQuery = useQuery<MatrixVersionDetail>({
    queryKey: ['matrix-version-detail', selectedVersionFromList?.id],
    enabled: Boolean(selectedVersionFromList?.id),
    queryFn: async () => {
      const response = await api.get(`/matrix/${selectedVersionFromList?.id}`);
      return response.data as MatrixVersionDetail;
    },
  });

  const comparisonQuery = useQuery<ComparisonView>({
    queryKey: ['matrix-comparison', selectedVersionFromList?.id],
    enabled: Boolean(selectedVersionFromList?.id) && activeView === 'comparison',
    queryFn: async () => {
      const response = await api.get(`/matrix/${selectedVersionFromList?.id}/comparison`);
      return response.data as ComparisonView;
    },
  });

  const buildMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/matrix/build', { project_id: projectId });
      return response.data as MatrixVersionDetail;
    },
    onSuccess: async (version) => {
      setSelectedVersionId(version.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ['matrix-versions', projectId] });
      await qc.invalidateQueries({ queryKey: ['matrix-version-detail', version.id] });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not build matrix');
    },
  });

  async function exportVersion(format: (typeof EXPORT_FORMATS)[number]) {
    if (!selectedVersionFromList?.id) return;
    try {
      const response = await api.get(`/matrix/${selectedVersionFromList.id}/export`, {
        params: { format },
        responseType: 'blob',
      });
      downloadBlob(response.data as Blob, `matrix_v${selectedVersionFromList.version_number}.${format}`);
      setError(null);
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Export failed');
    }
  }

  if (!projectId) {
    return <div className="rc-error">Missing project id</div>;
  }

  const detail = detailQuery.data;
  const previewRows = (detail?.rows || []).slice(0, 8);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Master Extraction Matrix</h1>
        <div className="rc-subtitle">
          Versioned, traceable matrix built from extraction outputs. Exportable as XLSX, CSV, JSON and XML.
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="rc-btn rc-btn--primary" onClick={() => buildMutation.mutate()} disabled={buildMutation.isPending}>
          {buildMutation.isPending ? 'Building matrix…' : 'Build new matrix version'}
        </button>
        <button className="rc-btn rc-btn--ghost" onClick={() => versionsQuery.refetch()} disabled={versionsQuery.isFetching}>
          {versionsQuery.isFetching ? 'Refreshing…' : 'Refresh versions'}
        </button>
        {EXPORT_FORMATS.map((format) => (
          <button
            key={format}
            className="rc-btn"
            onClick={() => exportVersion(format)}
            disabled={!selectedVersionFromList}
          >
            Export {format.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'minmax(260px, 340px) minmax(0, 1fr)' }}>
        <section className="rc-card">
          <div className="rc-card-title">Versions</div>
          {(versionsQuery.data || []).length === 0 ? <div className="rc-muted">No matrix versions yet.</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(versionsQuery.data || []).map((version) => (
              <button
                key={version.id}
                className="rc-btn"
                style={{
                  textAlign: 'left',
                  alignItems: 'flex-start',
                  flexDirection: 'column',
                  gap: 4,
                  borderColor: selectedVersionFromList?.id === version.id ? 'rgba(79,70,229,0.35)' : undefined,
                  background: selectedVersionFromList?.id === version.id ? 'var(--rc-primary-weak)' : undefined,
                }}
                onClick={() => setSelectedVersionId(version.id)}
              >
                <div style={{ fontWeight: 700 }}>
                  v{version.version_number} {version.is_current ? '· current' : ''}
                </div>
                <div className="rc-help">{version.status} · {formatDate(version.created_at)}</div>
                <div className="rc-help">
                  rows {version.summary?.rows_total ?? 0} · effects {version.summary?.effects ?? 0}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="rc-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
            <div className="rc-card-title" style={{ marginBottom: 0 }}>
              {activeView === 'comparison' ? 'Literature comparison' : 'Selected version detail'}
            </div>
            <div role="tablist" style={{ display: 'inline-flex', borderRadius: 999, background: 'var(--rc-surface-2)', padding: 3 }}>
              <button
                role="tab"
                aria-selected={activeView === 'detail'}
                onClick={() => setActiveView('detail')}
                className="rc-btn"
                style={{
                  fontSize: 12, padding: '6px 12px', borderRadius: 999, border: 'none',
                  background: activeView === 'detail' ? 'var(--rc-primary)' : 'transparent',
                  color: activeView === 'detail' ? 'white' : 'var(--rc-text-secondary)',
                  fontWeight: 600,
                }}
              >
                Detail
              </button>
              <button
                role="tab"
                aria-selected={activeView === 'comparison'}
                onClick={() => setActiveView('comparison')}
                className="rc-btn"
                style={{
                  fontSize: 12, padding: '6px 12px', borderRadius: 999, border: 'none',
                  background: activeView === 'comparison' ? 'var(--rc-primary)' : 'transparent',
                  color: activeView === 'comparison' ? 'white' : 'var(--rc-text-secondary)',
                  fontWeight: 600,
                }}
              >
                Comparison
              </button>
            </div>
          </div>

          {activeView === 'comparison' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {comparisonQuery.isLoading ? <div className="rc-muted">Loading comparison…</div> : null}
              {comparisonQuery.error ? <div className="rc-error">Could not load comparison.</div> : null}
              {comparisonQuery.data && comparisonQuery.data.rows.length === 0 ? (
                <div className="rc-muted">No studies found in this matrix version.</div>
              ) : null}
              {comparisonQuery.data && comparisonQuery.data.rows.length > 0 ? (
                <div style={{ overflowX: 'auto', border: '1px solid var(--rc-border)', borderRadius: 10 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ background: 'var(--rc-surface-2)' }}>
                        {comparisonQuery.data.columns.map((col) => (
                          <th
                            key={col.key}
                            style={{
                              textAlign: 'left',
                              padding: '10px 12px',
                              fontWeight: 700,
                              fontSize: 12,
                              textTransform: 'uppercase',
                              letterSpacing: 0.4,
                              color: 'var(--rc-text-secondary)',
                              borderBottom: '1px solid var(--rc-border)',
                              whiteSpace: 'nowrap',
                              position: col.key === 'study' ? 'sticky' : undefined,
                              left: col.key === 'study' ? 0 : undefined,
                              background: col.key === 'study' ? 'var(--rc-surface-2)' : undefined,
                              zIndex: col.key === 'study' ? 2 : undefined,
                            }}
                          >
                            {col.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {comparisonQuery.data.rows.map((row, idx) => (
                        <tr key={row.study_id || row.paper_id || idx} style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(148,163,184,0.05)' }}>
                          {comparisonQuery.data!.columns.map((col) => (
                            <td
                              key={col.key}
                              style={{
                                padding: '10px 12px',
                                verticalAlign: 'top',
                                borderBottom: '1px solid var(--rc-border-subtle, rgba(148,163,184,0.18))',
                                fontWeight: col.key === 'study' ? 600 : 400,
                                color: 'var(--rc-text)',
                                position: col.key === 'study' ? 'sticky' : undefined,
                                left: col.key === 'study' ? 0 : undefined,
                                background: col.key === 'study'
                                  ? (idx % 2 === 0 ? 'var(--rc-surface)' : 'var(--rc-surface-2)')
                                  : undefined,
                                minWidth: col.key === 'study' ? 220 : 140,
                                maxWidth: 320,
                              }}
                            >
                              {row.cells[col.key] || '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          ) : null}

          {activeView === 'detail' && !detail ? <div className="rc-muted">Select a matrix version.</div> : null}

          {activeView === 'detail' && detail ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="rc-help">
                schema {detail.schema_version} · status {detail.status} · created {formatDate(detail.created_at)}
              </div>

              <div className="rc-product-two-column" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">Rows total</div>
                  <div style={{ fontWeight: 800, fontSize: 24 }}>{detail.summary?.rows_total ?? 0}</div>
                </div>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">Effects</div>
                  <div style={{ fontWeight: 800, fontSize: 24 }}>{detail.summary?.effects ?? 0}</div>
                </div>
                <div className="rc-card" style={{ padding: 12 }}>
                  <div className="rc-kicker">Validation issues</div>
                  <div style={{ fontWeight: 800, fontSize: 24 }}>{detail.validation_issues.length}</div>
                </div>
              </div>

              <div className="rc-card" style={{ padding: 12 }}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Row preview</div>
                {previewRows.length === 0 ? <div className="rc-muted">No rows.</div> : null}
                {previewRows.map((row, index) => (
                  <pre
                    key={String(row.row_id || index)}
                    style={{
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      fontSize: 12,
                      background: 'rgba(148,163,184,0.08)',
                      padding: 8,
                      borderRadius: 8,
                      marginBottom: 8,
                    }}
                  >
                    {JSON.stringify(row, null, 2)}
                  </pre>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { downloadBlob } from '../components/meta/exportUtils';

type MatrixVersionRow = {
  id: string;
  version_number: number;
  is_current: boolean;
};

type DerivedDataset = {
  id: string;
  project_id: string;
  matrix_version_id: string;
  title: string;
  preset: string;
  status: string;
  row_count: number;
  column_count: number;
  created_at?: string | null;
};

type MetaArtifact = {
  id: string;
  artifact_type: string;
  filename: string;
  file_path: string;
  mime_type: string;
};

type MetaRun = {
  id: string;
  title: string;
  preset: string;
  status: string;
  warnings: string[];
  summary: Record<string, unknown>;
  created_at?: string | null;
  artifacts: MetaArtifact[];
};

const PRESETS = [
  'meta_binary_random',
  'meta_binary_fixed',
  'meta_continuous_md',
  'meta_continuous_smd',
  'meta_generic_iv',
  'meta_survival_hr',
  'meta_proportion',
  'meta_diag_accuracy',
  'risk_of_bias_summary',
  'publication_bias_suite',
] as const;

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
}

export default function MetaRunsPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();
  const [datasetTitle, setDatasetTitle] = useState('derived_dataset');
  const [preset, setPreset] = useState<(typeof PRESETS)[number]>('meta_binary_random');
  const [matrixVersionId, setMatrixVersionId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [runTitle, setRunTitle] = useState('meta run');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const matrixVersionsQuery = useQuery<MatrixVersionRow[]>({
    queryKey: ['matrix-versions-compact', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/matrix/versions', { params: { project_id: projectId } });
      return response.data as MatrixVersionRow[];
    },
  });

  const datasetsQuery = useQuery<DerivedDataset[]>({
    queryKey: ['derived-datasets', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/datasets/derived', { params: { project_id: projectId } });
      return response.data as DerivedDataset[];
    },
  });

  const runsQuery = useQuery<MetaRun[]>({
    queryKey: ['meta-runs', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/meta/runs', { params: { project_id: projectId } });
      return response.data as MetaRun[];
    },
  });

  const deriveMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/datasets/derive', {
        project_id: projectId,
        matrix_version_id: matrixVersionId || null,
        preset,
        title: datasetTitle.trim() || null,
      });
      return response.data as DerivedDataset;
    },
    onSuccess: async (dataset) => {
      setSelectedDatasetId(dataset.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ['derived-datasets', projectId] });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not derive dataset');
    },
  });

  const runMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/meta/runs', {
        project_id: projectId,
        derived_dataset_id: selectedDatasetId,
        preset,
        title: runTitle.trim() || null,
      });
      return response.data as MetaRun;
    },
    onSuccess: async (run) => {
      setSelectedRunId(run.id);
      setError(null);
      await qc.invalidateQueries({ queryKey: ['meta-runs', projectId] });
    },
    onError: (e: unknown) => {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not run meta analysis');
    },
  });

  const selectedRun = useMemo(() => {
    if (!runsQuery.data || runsQuery.data.length === 0) return null;
    if (selectedRunId) return runsQuery.data.find((item) => item.id === selectedRunId) || null;
    return runsQuery.data[0];
  }, [runsQuery.data, selectedRunId]);

  async function downloadArtifact(artifactId: string, fallbackFilename: string) {
    try {
      const response = await api.get(`/artifacts/${artifactId}/download`, { responseType: 'blob' });
      downloadBlob(response.data as Blob, fallbackFilename);
      setError(null);
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Could not download artifact');
    }
  }

  if (!projectId) {
    return <div className="rc-error">Missing project id</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Meta Runs</h1>
        <div className="rc-subtitle">
          Derive analytical datasets from the matrix and execute reproducible R-driven meta runs with publication artifacts.
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
        <section className="rc-card">
          <div className="rc-card-title">1) Derive dataset</div>

          <label className="rc-discover-filter-field">
            <span>Preset</span>
            <select className="rc-input" value={preset} onChange={(e) => setPreset(e.target.value as (typeof PRESETS)[number])}>
              {PRESETS.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>

          <label className="rc-discover-filter-field">
            <span>Matrix version (optional: current)</span>
            <select className="rc-input" value={matrixVersionId} onChange={(e) => setMatrixVersionId(e.target.value)}>
              <option value="">Current matrix version</option>
              {(matrixVersionsQuery.data || []).map((version) => (
                <option key={version.id} value={version.id}>
                  v{version.version_number}{version.is_current ? ' (current)' : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="rc-discover-filter-field">
            <span>Dataset title</span>
            <input className="rc-input" value={datasetTitle} onChange={(e) => setDatasetTitle(e.target.value)} />
          </label>

          <button className="rc-btn rc-btn--primary" onClick={() => deriveMutation.mutate()} disabled={deriveMutation.isPending}>
            {deriveMutation.isPending ? 'Deriving dataset…' : 'Derive dataset'}
          </button>
        </section>

        <section className="rc-card">
          <div className="rc-card-title">2) Run meta analysis</div>
          <label className="rc-discover-filter-field">
            <span>Derived dataset</span>
            <select className="rc-input" value={selectedDatasetId} onChange={(e) => setSelectedDatasetId(e.target.value)}>
              <option value="">Select dataset</option>
              {(datasetsQuery.data || []).map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.title} · {dataset.preset} · {dataset.row_count} rows
                </option>
              ))}
            </select>
          </label>

          <label className="rc-discover-filter-field">
            <span>Run title</span>
            <input className="rc-input" value={runTitle} onChange={(e) => setRunTitle(e.target.value)} />
          </label>

          <button
            className="rc-btn rc-btn--primary"
            onClick={() => runMutation.mutate()}
            disabled={!selectedDatasetId || runMutation.isPending}
          >
            {runMutation.isPending ? 'Running…' : 'Create meta run'}
          </button>
        </section>
      </div>

      <div className="rc-workspace-grid" style={{ gridTemplateColumns: 'minmax(260px, 360px) minmax(0, 1fr)' }}>
        <section className="rc-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="rc-card-title" style={{ margin: 0 }}>Runs</div>
            <button className="rc-btn rc-btn--sm rc-btn--ghost" aria-label="Refresh" title="Refresh" onClick={() => runsQuery.refetch()} disabled={runsQuery.isFetching}>
              {runsQuery.isFetching ? '…' : '↻'}
            </button>
          </div>

          {(runsQuery.data || []).length === 0 ? <div className="rc-muted">No meta runs yet.</div> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(runsQuery.data || []).map((run) => (
              <button
                key={run.id}
                className="rc-btn"
                style={{
                  textAlign: 'left',
                  alignItems: 'flex-start',
                  flexDirection: 'column',
                  gap: 4,
                  borderColor: selectedRun?.id === run.id ? 'rgba(79,70,229,0.35)' : undefined,
                  background: selectedRun?.id === run.id ? 'var(--rc-primary-weak)' : undefined,
                }}
                onClick={() => setSelectedRunId(run.id)}
              >
                <div style={{ fontWeight: 700 }}>{run.title}</div>
                <div className="rc-help">{run.preset}</div>
                <div className="rc-help">{run.status} · {formatDate(run.created_at)}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="rc-card">
          <div className="rc-card-title">Run artifacts</div>
          {!selectedRun ? <div className="rc-muted">Select a run to inspect artifacts.</div> : null}
          {selectedRun ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="rc-help">
                preset <b>{selectedRun.preset}</b> · status <b>{selectedRun.status}</b> · artifacts <b>{selectedRun.artifacts.length}</b>
              </div>

              {(selectedRun.warnings || []).length > 0 ? (
                <div className="rc-card" style={{ padding: 10, borderColor: 'rgba(245,158,11,0.3)' }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Warnings</div>
                  {(selectedRun.warnings || []).map((warning) => (
                    <div key={warning} className="rc-help">{warning}</div>
                  ))}
                </div>
              ) : null}

              {selectedRun.artifacts.length === 0 ? <div className="rc-muted">No artifacts.</div> : null}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 }}>
                {selectedRun.artifacts.map((artifact) => (
                  <div key={artifact.id} className="rc-card" style={{ padding: 10 }}>
                    <div style={{ fontWeight: 700, fontSize: 13 }}>{artifact.artifact_type}</div>
                    <div className="rc-help" style={{ marginBottom: 8 }}>{artifact.filename}</div>
                    <button className="rc-btn rc-btn--sm" onClick={() => downloadArtifact(artifact.id, artifact.filename)}>
                      Download
                    </button>
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

import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { downloadBlob } from '../components/meta/exportUtils';

type MetaArtifact = {
  id: string;
  artifact_type: string;
  filename: string;
  mime_type: string;
};

type MetaRun = {
  id: string;
  title: string;
  preset: string;
  status: string;
  created_at?: string | null;
  artifacts: MetaArtifact[];
};

type ArtifactRow = MetaArtifact & {
  run_id: string;
  run_title: string;
  preset: string;
  created_at?: string | null;
};

function formatDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString();
}

export default function ArtifactsPage() {
  const { projectId } = useParams();
  const [filter, setFilter] = useState('');
  const [error, setError] = useState<string | null>(null);

  const runsQuery = useQuery<MetaRun[]>({
    queryKey: ['artifacts-runs', projectId],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const response = await api.get('/meta/runs', { params: { project_id: projectId } });
      return response.data as MetaRun[];
    },
  });

  const artifacts = useMemo<ArtifactRow[]>(() => {
    const rows: ArtifactRow[] = [];
    for (const run of runsQuery.data || []) {
      for (const artifact of run.artifacts || []) {
        rows.push({
          ...artifact,
          run_id: run.id,
          run_title: run.title,
          preset: run.preset,
          created_at: run.created_at,
        });
      }
    }
    rows.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
    return rows;
  }, [runsQuery.data]);

  const filteredArtifacts = artifacts.filter((item) => {
    if (!filter.trim()) return true;
    const needle = filter.trim().toLowerCase();
    return (
      item.artifact_type.toLowerCase().includes(needle) ||
      item.filename.toLowerCase().includes(needle) ||
      item.run_title.toLowerCase().includes(needle) ||
      item.preset.toLowerCase().includes(needle)
    );
  });

  async function downloadArtifact(artifactId: string, filename: string) {
    try {
      const response = await api.get(`/artifacts/${artifactId}/download`, { responseType: 'blob' });
      downloadBlob(response.data as Blob, filename);
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
        <h1 className="rc-page-title">Artifacts</h1>
        <div className="rc-subtitle">
          Central artifact catalog for matrix exports, meta scripts, summary tables and publication-ready figures.
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          className="rc-input"
          style={{ minWidth: 300 }}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by type, filename, run or preset"
        />
        <button className="rc-btn rc-btn--ghost" onClick={() => runsQuery.refetch()} disabled={runsQuery.isFetching}>
          {runsQuery.isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Artifact list</div>
        {filteredArtifacts.length === 0 ? <div className="rc-muted">No artifacts found.</div> : null}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 10 }}>
          {filteredArtifacts.map((artifact) => (
            <div key={artifact.id} className="rc-card" style={{ padding: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 13 }}>{artifact.artifact_type}</div>
              <div className="rc-help">{artifact.filename}</div>
              <div className="rc-help" style={{ marginBottom: 8 }}>
                {artifact.run_title} · {artifact.preset} · {formatDate(artifact.created_at)}
              </div>
              <button className="rc-btn rc-btn--sm" onClick={() => downloadArtifact(artifact.id, artifact.filename)}>
                Download
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

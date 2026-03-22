import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

type Dataset = {
  id: string;
  title: string;
  row_count: number;
  column_count: number;
};

type AnalysisRun = {
  id: string;
  title: string;
  analysis_type: string;
  status: string;
  warnings: string[];
};

export default function AnalysisPage() {
  const { projectId } = useParams();
  const qc = useQueryClient();

  const [datasetTitle, setDatasetTitle] = useState('demo_dataset');
  const [rowsText, setRowsText] = useState('[{"group":"A","value":12},{"group":"A","value":10},{"group":"B","value":18}]');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [analysisTitle, setAnalysisTitle] = useState('Group comparison');
  const [analysisType, setAnalysisType] = useState('group_comparison');
  const [runs, setRuns] = useState<AnalysisRun[]>([]);

  const { data: datasets = [], isError } = useQuery<Dataset[]>({
    queryKey: ['datasets', projectId],
    queryFn: async () => {
      const r = await api.get('/datasets', { params: { project_id: projectId } });
      const data = r.data as Dataset[];
      if (!selectedDataset && data[0]) setSelectedDataset(data[0].id);
      return data;
    },
    enabled: !!projectId,
  });

  function invalidate() { qc.invalidateQueries({ queryKey: ['datasets', projectId] }); }

  const datasetMut = useMutation({
    mutationFn: () => {
      const rows = JSON.parse(rowsText) as Array<Record<string, unknown>>;
      return api.post('/datasets', { project_id: projectId, title: datasetTitle, rows });
    },
    onSuccess: (r) => {
      setSelectedDataset((r.data as Dataset).id);
      invalidate();
    },
    onError: () => {},
  });

  const runMut = useMutation({
    mutationFn: () => api.post('/analysis-runs', {
      project_id: projectId,
      dataset_id: selectedDataset || null,
      title: analysisTitle,
      analysis_type: analysisType,
      input_params:
        analysisType === 'group_comparison'
          ? { group_column: 'group', value_column: 'value' }
          : analysisType === 'linear_regression'
            ? { target_column: 'value', feature_columns: ['group'] }
            : {},
    }),
    onSuccess: (r) => setRuns((prev) => [r.data as AnalysisRun, ...prev]),
    onError: () => {},
  });

  async function exportRun(runId: string, format: 'html' | 'pdf' | 'docx') {
    try {
      const response = await api.post(`/analysis-runs/${runId}/export`, null, { params: { format }, responseType: 'blob' });
      const blob = response.data as Blob;
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${runId}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch { /* download errors are not critical */ }
  }

  const busy = datasetMut.isPending || runMut.isPending;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Analysis</h1>
        <div className="rc-subtitle">Create datasets from JSON rows and launch reproducible runs through the FastAPI orchestration layer.</div>
      </div>

      {isError && <div className="rc-error-card">Failed to load analysis workspace</div>}

      <div className="rc-card">
        <div className="rc-card-title">Dataset builder</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Dataset title</div>
            <input className="rc-input" value={datasetTitle} onChange={(e) => setDatasetTitle(e.target.value)} />
          </div>
          <button className="rc-btn rc-btn--primary" onClick={() => datasetMut.mutate()} disabled={busy}>Create dataset</button>
        </div>
        <div style={{ height: 10 }} />
        <textarea className="rc-input" style={{ minHeight: 140, width: '100%' }} value={rowsText} onChange={(e) => setRowsText(e.target.value)} />
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Run analysis</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Dataset</div>
            <select className="rc-input" value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
              <option value="">No dataset</option>
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.title} · {dataset.row_count} rows
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Title</div>
            <input className="rc-input" value={analysisTitle} onChange={(e) => setAnalysisTitle(e.target.value)} />
          </div>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Type</div>
            <select className="rc-input" value={analysisType} onChange={(e) => setAnalysisType(e.target.value)}>
              <option value="descriptives">Descriptives</option>
              <option value="group_comparison">Group comparison</option>
              <option value="linear_regression">Linear regression</option>
              <option value="logistic_regression">Logistic regression</option>
              <option value="meta_analysis">Meta-analysis</option>
            </select>
          </div>
          <button className="rc-btn" onClick={() => runMut.mutate()} disabled={busy}>
            {runMut.isPending ? 'Running...' : 'Run'}
          </button>
        </div>
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Datasets</div>
        {datasets.length === 0 ? <div className="rc-muted">No datasets yet.</div> : null}
        {datasets.map((dataset) => (
          <div key={dataset.id} className="rc-help">
            {dataset.title} · {dataset.row_count} rows · {dataset.column_count} columns
          </div>
        ))}
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Recent runs</div>
        {runs.length === 0 ? <div className="rc-muted">No analysis runs in this session yet.</div> : null}
        {runs.map((run) => (
          <div key={run.id} className="rc-card" style={{ padding: 12, marginBottom: 10 }}>
            <div style={{ fontWeight: 800 }}>{run.title}</div>
            <div className="rc-help">{run.analysis_type} · {run.status}</div>
            {run.warnings?.length ? <div className="rc-help">Warnings: {run.warnings.join(' | ')}</div> : null}
            <div className="rc-row">
              <button className="rc-btn" onClick={() => exportRun(run.id, 'html')}>HTML</button>
              <button className="rc-btn" onClick={() => exportRun(run.id, 'pdf')}>PDF</button>
              <button className="rc-btn" onClick={() => exportRun(run.id, 'docx')}>DOCX</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

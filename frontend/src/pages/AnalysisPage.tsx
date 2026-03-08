import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
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
  runtime_metadata?: { job_id?: string; artifact_manifest?: Array<{ format?: string; artifact_type?: string }> };
};

export default function AnalysisPage() {
  const { projectId } = useParams();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [datasetTitle, setDatasetTitle] = useState('demo_dataset');
  const [rowsText, setRowsText] = useState('[{"group":"A","value":12},{"group":"A","value":10},{"group":"B","value":18}]');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [analysisTitle, setAnalysisTitle] = useState('Group comparison');
  const [analysisType, setAnalysisType] = useState('group_comparison');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!projectId) return;
    const [datasetResponse, runResponse] = await Promise.all([
      api.get('/datasets', { params: { project_id: projectId } }),
      api.get('/analysis-runs', { params: { project_id: projectId } }),
    ]);
    const nextDatasets = datasetResponse.data as Dataset[];
    setDatasets(nextDatasets);
    setRuns(runResponse.data as AnalysisRun[]);
    if (!selectedDataset && nextDatasets[0]) {
      setSelectedDataset(nextDatasets[0].id);
    }
  }

  useEffect(() => {
    load().catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load analysis workspace'));
  }, [projectId]);

  useEffect(() => {
    if (!runs.some((run) => run.status === 'queued' || run.status === 'running')) return;
    const timer = window.setInterval(() => {
      void load().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [runs, projectId]);

  async function createDataset() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      const rows = JSON.parse(rowsText) as Array<Record<string, unknown>>;
      const response = await api.post('/datasets', { project_id: projectId, title: datasetTitle, rows });
      const dataset = response.data as Dataset;
      setSelectedDataset(dataset.id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to create dataset');
    } finally {
      setBusy(false);
    }
  }

  async function createRun() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      const response = await api.post('/analysis-runs', {
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
      });
      setRuns((prev) => [response.data as AnalysisRun, ...prev]);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setBusy(false);
    }
  }

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
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to export analysis');
    }
  }

  return (
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-stage-label rc-stage-label--teal">Step 5 · Analyze</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Analysis</h1>
          <div className="rc-subtitle">Create datasets, launch runs and export HTML, PDF or DOCX reports through the analysis engine.</div>
          <div className="rc-help" style={{ marginTop: 12 }}>Use this stage when you want formal outputs, tables and reproducible reports from the evidence you've already curated.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 300 }}>
          <div className="rc-metric-tile"><strong>{datasets.length}</strong><span>Datasets</span></div>
          <div className="rc-metric-tile"><strong>{runs.length}</strong><span>Runs</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-panel-grid" style={{ alignItems: 'start' }}>
        <div className="rc-card">
          <div className="rc-card-title">Dataset builder</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Dataset title</div>
              <input data-testid="dataset-title-input" className="rc-input" value={datasetTitle} onChange={(e) => setDatasetTitle(e.target.value)} />
            </div>
            <button data-testid="dataset-create-button" className="rc-btn rc-btn--primary" onClick={createDataset} disabled={busy}>Create dataset</button>
          </div>
          <div style={{ height: 10 }} />
          <textarea data-testid="dataset-rows-input" className="rc-input" style={{ minHeight: 140, width: '100%' }} value={rowsText} onChange={(e) => setRowsText(e.target.value)} />
        </div>

        <div className="rc-card">
          <div className="rc-card-title">Run analysis</div>
          <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Dataset</div>
              <select data-testid="analysis-dataset-select" className="rc-input" value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
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
              <input data-testid="analysis-title-input" className="rc-input" value={analysisTitle} onChange={(e) => setAnalysisTitle(e.target.value)} />
            </div>
            <div style={{ minWidth: 220 }}>
              <div className="rc-kicker">Type</div>
              <select data-testid="analysis-type-select" className="rc-input" value={analysisType} onChange={(e) => setAnalysisType(e.target.value)}>
                <option value="descriptives">Descriptives</option>
                <option value="group_comparison">Group comparison</option>
                <option value="linear_regression">Linear regression</option>
                <option value="logistic_regression">Logistic regression</option>
                <option value="meta_analysis">Meta-analysis</option>
              </select>
            </div>
            <button data-testid="analysis-run-button" className="rc-btn" onClick={createRun} disabled={busy}>Run</button>
          </div>
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
          <div data-testid={`analysis-run-${run.id}`} key={run.id} className="rc-soft-card" style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 800 }}>{run.title}</div>
            <div className="rc-help">{run.analysis_type} · {run.status}</div>
            {run.runtime_metadata?.job_id ? <div className="rc-help">Job: {run.runtime_metadata.job_id}</div> : null}
            {run.warnings?.length ? <div className="rc-help">Warnings: {run.warnings.join(' | ')}</div> : null}
            <div className="rc-row">
              <button data-testid={`analysis-export-html-${run.id}`} className="rc-btn" onClick={() => exportRun(run.id, 'html')} disabled={run.status !== 'completed'}>HTML</button>
              <button data-testid={`analysis-export-pdf-${run.id}`} className="rc-btn" onClick={() => exportRun(run.id, 'pdf')} disabled={run.status !== 'completed'}>PDF</button>
              <button data-testid={`analysis-export-docx-${run.id}`} className="rc-btn" onClick={() => exportRun(run.id, 'docx')} disabled={run.status !== 'completed'}>DOCX</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

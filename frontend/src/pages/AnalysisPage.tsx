import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { EmptyState } from '../components/EmptyState';

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

function mergeRunsWithPending(currentRuns: AnalysisRun[], loadedRuns: AnalysisRun[]) {
  const loadedById = new Set(loadedRuns.map((run) => run.id));
  const pendingRuns = currentRuns.filter((run) => run.id.startsWith('pending-') && !loadedById.has(run.id));
  return [...pendingRuns, ...loadedRuns];
}

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
  const [creatingDataset, setCreatingDataset] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      const [datasetResponse, runResponse] = await Promise.all([
        api.get('/datasets', { params: { project_id: projectId } }),
        api.get('/analysis-runs', { params: { project_id: projectId } }),
      ]);
      const nextDatasets = datasetResponse.data as Dataset[];
      const nextRuns = runResponse.data as AnalysisRun[];
      setDatasets(nextDatasets);
      setRuns((currentRuns) => mergeRunsWithPending(currentRuns, nextRuns));
      if (!selectedDataset && nextDatasets[0]) {
        setSelectedDataset(nextDatasets[0].id);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load analysis workspace');
    } finally {
      setInitialLoading(false);
    }
  }, [projectId, selectedDataset]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!runs.some((run) => ['queued', 'started', 'running', 'progress'].includes(run.status))) return;
    const interval = window.setInterval(() => {
      load().catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(interval);
  }, [load, runs]);

  async function createDataset() {
    if (!projectId) return;
    setCreatingDataset(true);
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
      setCreatingDataset(false);
    }
  }

  async function createRun() {
    if (!projectId) return;
    setRunningAnalysis(true);
    setError(null);
    const optimisticRunId = `pending-${Date.now()}`;
    setRuns((prev) => [
      {
        id: optimisticRunId,
        title: analysisTitle,
        analysis_type: analysisType,
        status: 'running',
        warnings: [],
      },
      ...prev,
    ]);
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
      setRuns((prev) => {
        const nextRun = response.data as AnalysisRun;
        const withoutOptimistic = prev.filter((run) => run.id !== optimisticRunId);
        return [nextRun, ...withoutOptimistic];
      });
    } catch (e: any) {
      setRuns((prev) => prev.filter((run) => run.id !== optimisticRunId));
      setError(e?.response?.data?.detail || 'Failed to run analysis');
    } finally {
      setRunningAnalysis(false);
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Analysis</h1>
        <div className="rc-subtitle">Create datasets from JSON rows and launch reproducible runs through the FastAPI orchestration layer.</div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}

      <div className="rc-card">
        <div className="rc-card-title">Dataset builder</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Dataset title</div>
            <input
              className="rc-input"
              data-testid="dataset-title-input"
              value={datasetTitle}
              onChange={(e) => setDatasetTitle(e.target.value)}
            />
          </div>
          <button className="rc-btn rc-btn--primary" data-testid="dataset-create-button" onClick={createDataset} disabled={creatingDataset}>Create dataset</button>
        </div>
        <div style={{ height: 10 }} />
        <textarea
          className="rc-input"
          data-testid="dataset-rows-input"
          style={{ minHeight: 140, width: '100%' }}
          value={rowsText}
          onChange={(e) => setRowsText(e.target.value)}
        />
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Run analysis</div>
        <div className="rc-row" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Dataset</div>
            <select
              className="rc-input"
              data-testid="analysis-dataset-select"
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
            >
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
            <input
              className="rc-input"
              data-testid="analysis-title-input"
              value={analysisTitle}
              onChange={(e) => setAnalysisTitle(e.target.value)}
            />
          </div>
          <div style={{ minWidth: 220 }}>
            <div className="rc-kicker">Type</div>
            <select
              className="rc-input"
              data-testid="analysis-type-select"
              value={analysisType}
              onChange={(e) => setAnalysisType(e.target.value)}
            >
              <option value="descriptives">Descriptives</option>
              <option value="group_comparison">Group comparison</option>
              <option value="linear_regression">Linear regression</option>
              <option value="logistic_regression">Logistic regression</option>
              <option value="meta_analysis">Meta-analysis</option>
            </select>
          </div>
          <button className="rc-btn" data-testid="analysis-run-button" onClick={createRun} disabled={creatingDataset || runningAnalysis}>Run</button>
        </div>
      </div>

      {/* Skeleton while initial data loads */}
      {initialLoading && (
        <div className="rc-page-skeleton">
          <div className="rc-skeleton-card" style={{ height: 80 }}>
            {[70, 50].map((w, i) => (
              <div key={i} className="rc-skeleton-line" style={{ width: `${w}%`, marginBottom: 8 }} />
            ))}
          </div>
          <div className="rc-skeleton-card" style={{ height: 60 }} />
        </div>
      )}

      {!initialLoading && <>
      <div className="rc-card">
        <div className="rc-card-title">Datasets</div>
        {datasets.length === 0 ? (
          <EmptyState variant="generic" title="No datasets yet" description="Create your first dataset using the builder above." />
        ) : null}
        {datasets.map((dataset) => (
          <div key={dataset.id} className="rc-help" style={{ padding: '6px 0', borderBottom: '1px solid var(--rc-border)' }}>
            <strong>{dataset.title}</strong> · {dataset.row_count} rows · {dataset.column_count} columns
          </div>
        ))}
      </div>

      <div className="rc-card">
        <div className="rc-card-title">Recent runs</div>
        {runs.length === 0 ? (
          <EmptyState variant="generic" title="No analysis runs yet" description="Configure and run an analysis above to see results here." />
        ) : null}
        {runs.map((run) => (
          <div key={run.id} className="rc-card rc-optimistic" data-testid={`analysis-run-${run.id}`} style={{ padding: 12, marginBottom: 10 }}>
            <div style={{ fontWeight: 800 }}>{run.title}</div>
            <div className="rc-help">{run.analysis_type} · {run.status}</div>
            {run.warnings?.length ? <div className="rc-help">Warnings: {run.warnings.join(' | ')}</div> : null}
            <div className="rc-row">
              <button className="rc-btn" data-testid={`analysis-export-${run.id}-html`} disabled={run.status !== 'completed'} onClick={() => exportRun(run.id, 'html')}>HTML</button>
              <button className="rc-btn" data-testid={`analysis-export-${run.id}-pdf`} disabled={run.status !== 'completed'} onClick={() => exportRun(run.id, 'pdf')}>PDF</button>
              <button className="rc-btn" data-testid={`analysis-export-${run.id}-docx`} disabled={run.status !== 'completed'} onClick={() => exportRun(run.id, 'docx')}>DOCX</button>
            </div>
          </div>
        ))}
      </div>
      </>}
    </div>
  );
}

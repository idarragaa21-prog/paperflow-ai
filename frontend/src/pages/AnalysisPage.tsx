import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useParams } from 'react-router-dom';

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
  const [datasetTitle, setDatasetTitle] = useState('dataset_demo');
  const [rowsText, setRowsText] = useState('[{"group":"A","value":12},{"group":"A","value":10},{"group":"B","value":18}]');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [analysisTitle, setAnalysisTitle] = useState('Comparacion de grupos');
  const [analysisType, setAnalysisType] = useState('group_comparison');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
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
    void load().catch((e: any) => setError(e?.response?.data?.detail || 'No se pudo cargar el espacio de análisis'));
  }, [projectId]);

  useEffect(() => {
    if (!runs.some((run) => run.status === 'queued' || run.status === 'running' || run.status === 'retry_pending')) return;
    const timer = window.setInterval(() => {
      void load().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [runs, projectId]);

  async function createDataset() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const rows = JSON.parse(rowsText) as Array<Record<string, unknown>>;
      const response = await api.post('/datasets', { project_id: projectId, title: datasetTitle, rows });
      const dataset = response.data as Dataset;
      setSelectedDataset(dataset.id);
      setNotice(`Conjunto de datos "${dataset.title}" creado.`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el dataset');
    } finally {
      setBusy(false);
    }
  }

  async function createRun() {
    if (!projectId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
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
      setNotice('La corrida quedó encolada. Su estado se refresca automáticamente.');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo ejecutar el análisis');
    } finally {
      setBusy(false);
    }
  }

  async function exportRun(runId: string, format: 'html' | 'pdf' | 'docx') {
    setError(null);
    setNotice(null);
    try {
      const response = await api.post(`/analysis-runs/${runId}/export`, null, {
        params: { format },
        responseType: 'blob',
      });
      const blob = response.data as Blob;
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${runId}.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setNotice(`Exportación ${format.toUpperCase()} lista.`);
    } catch (e: any) {
      if (e?.response?.data instanceof Blob) {
        try {
          const text = await e.response.data.text();
          const payload = JSON.parse(text);
          setError(payload?.detail || 'No se pudo exportar el análisis');
          return;
        } catch {
          // ignore
        }
      }
      setError(e?.response?.data?.detail || 'No se pudo exportar el análisis');
    }
  }

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Análisis reproducible</div>
          <h2>Convierte datasets en corridas y reportes exportables</h2>
          <p>
            Crea datasets mínimos, encola análisis y exporta HTML, PDF o DOCX sin salir del proyecto.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{datasets.length} datasets</span>
          <span className="rc-discover-badge">{runs.length} corridas</span>
        </div>
      </div>

      {error ? <div className="rc-error">{error}</div> : null}
      {notice ? <div className="rc-help">{notice}</div> : null}

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Construir dataset</div>
              <div className="rc-help">Usa un JSON simple para generar un dataset y dejarlo listo para análisis.</div>
            </div>
          </div>

          <div className="rc-product-form-grid">
            <label className="rc-discover-filter-field">
              <span>Título del dataset</span>
              <input data-testid="dataset-title-input" className="rc-input" value={datasetTitle} onChange={(e) => setDatasetTitle(e.target.value)} />
            </label>
          </div>

          <textarea
            data-testid="dataset-rows-input"
            className="rc-discover-composer__input rc-product-textarea"
            value={rowsText}
            onChange={(e) => setRowsText(e.target.value)}
          />

          <button data-testid="dataset-create-button" className="rc-btn rc-btn--primary" onClick={() => void createDataset()} disabled={busy}>
            Crear conjunto de datos
          </button>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Lanzar análisis</div>
              <div className="rc-help">Selecciona dataset, define el tipo y deja la corrida en la cola de análisis.</div>
            </div>
          </div>

          <div className="rc-product-form-grid rc-product-form-grid--three">
            <label className="rc-discover-filter-field">
              <span>Dataset</span>
              <select data-testid="analysis-dataset-select" className="rc-input" value={selectedDataset} onChange={(e) => setSelectedDataset(e.target.value)}>
                <option value="">Sin conjunto de datos</option>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.title} · {dataset.row_count} filas
                  </option>
                ))}
              </select>
            </label>

            <label className="rc-discover-filter-field">
              <span>Título</span>
              <input data-testid="analysis-title-input" className="rc-input" value={analysisTitle} onChange={(e) => setAnalysisTitle(e.target.value)} />
            </label>

            <label className="rc-discover-filter-field">
              <span>Tipo</span>
              <select data-testid="analysis-type-select" className="rc-input" value={analysisType} onChange={(e) => setAnalysisType(e.target.value)}>
                <option value="descriptives">Descriptivos</option>
                <option value="group_comparison">Comparación de grupos</option>
                <option value="linear_regression">Regresión lineal</option>
                <option value="logistic_regression">Regresión logística</option>
                <option value="meta_analysis">Metaanálisis</option>
              </select>
            </label>
          </div>

          <button data-testid="analysis-run-button" className="rc-btn rc-btn--primary" onClick={() => void createRun()} disabled={busy}>
            Ejecutar análisis
          </button>
        </section>
      </div>

      <div className="rc-product-two-column">
        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Datasets disponibles</div>
            </div>
          </div>
          {datasets.length === 0 ? <div className="rc-muted">Todavía no hay conjuntos de datos.</div> : null}
          <div className="rc-discover-card-list">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="rc-discover-result-card">
                <div className="rc-discover-result-card__header">
                  <div>
                    <h3 className="rc-discover-result-card__title" style={{ fontSize: 24 }}>{dataset.title}</h3>
                    <div className="rc-discover-result-card__journal">{dataset.row_count} filas · {dataset.column_count} columnas</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rc-product-card">
          <div className="rc-product-card__header">
            <div>
              <div className="rc-card-title">Corridas recientes</div>
              <div className="rc-help">Las corridas muestran su estado real y solo habilitan export cuando ya están completas.</div>
            </div>
          </div>

          <div className="rc-discover-card-list">
            {runs.length === 0 ? <div className="rc-muted">Todavía no hay corridas de análisis.</div> : null}
            {runs.map((run) => (
              <div data-testid={`analysis-run-${run.id}`} key={run.id} className="rc-discover-result-card">
                <div className="rc-discover-result-card__header">
                  <div style={{ flex: 1 }}>
                    <h3 className="rc-discover-result-card__title" style={{ fontSize: 26 }}>{run.title}</h3>
                    <div className="rc-discover-result-card__journal">{run.analysis_type} · {run.status}</div>
                  </div>
                  <div className="rc-discover-badges">
                    <span className="rc-discover-badge">{run.status}</span>
                    {run.runtime_metadata?.job_id ? <span className="rc-discover-badge">Job: {run.runtime_metadata.job_id}</span> : null}
                  </div>
                </div>
                {run.runtime_metadata?.artifact_manifest?.length ? (
                  <div className="rc-help">
                    Artefactos: {run.runtime_metadata.artifact_manifest.map((item) => item.format || item.artifact_type).join(', ')}
                  </div>
                ) : null}
                {run.warnings?.length ? <div className="rc-help">Alertas: {run.warnings.join(' · ')}</div> : null}
                <div className="rc-row">
                  <button data-testid={`analysis-export-html-${run.id}`} className="rc-btn rc-btn--subtle" onClick={() => void exportRun(run.id, 'html')} disabled={run.status !== 'completed'}>HTML</button>
                  <button data-testid={`analysis-export-pdf-${run.id}`} className="rc-btn rc-btn--subtle" onClick={() => void exportRun(run.id, 'pdf')} disabled={run.status !== 'completed'}>PDF</button>
                  <button data-testid={`analysis-export-docx-${run.id}`} className="rc-btn rc-btn--subtle" onClick={() => void exportRun(run.id, 'docx')} disabled={run.status !== 'completed'}>DOCX</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import StudyViewer from '../components/meta/StudyViewer';
import { downloadBlob } from '../components/meta/exportUtils';
import { api } from '../services/api';

type BatchRow = {
  id: string;
  title?: string | null;
  status: string;
  created_at: string;
};

type ItemRow = {
  id: string;
  paper_id: string;
  paper_title?: string;
  paper_filename?: string;
  status: string;
  error_message?: string | null;
  result_summary?: any;
  created_at?: string | null;
  updated_at?: string | null;
};

type StudyRow = {
  id: string;
  paper_id: string;
  paper_title?: string;
  paper_filename?: string;
  batch_id?: string | null;
  version: number;
  extraction_confidence: number;
  rob_auto_generated?: boolean;
  created_at: string;
};

type ExportRow = {
  id: string;
  project_id: string;
  batch_id?: string | null;
  filename: string;
  created_at: string;
};

function formatDate(value?: string | null) {
  if (!value) return 'Hora desconocida';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function MetaPage() {
  const { projectId } = useParams();

  const [batches, setBatches] = useState<BatchRow[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null);
  const [items, setItems] = useState<ItemRow[]>([]);
  const [studies, setStudies] = useState<StudyRow[]>([]);
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [exportsList, setExportsList] = useState<ExportRow[]>([]);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [exportJobStatus, setExportJobStatus] = useState<{ status: string; progress: number; error?: string | null } | null>(null);
  const [files, setFiles] = useState<FileList | null>(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const runningItems = useMemo(() => items.filter((it) => ['queued', 'started'].includes(it.status)), [items]);
  const completedItems = useMemo(() => items.filter((it) => it.status === 'completed').length, [items]);
  const failedItems = useMemo(() => items.filter((it) => it.status === 'failed').length, [items]);
  const selectedBatch = useMemo(() => batches.find((batch) => batch.id === selectedBatchId) || null, [batches, selectedBatchId]);
  const selectedFilesCount = files?.length || 0;

  async function loadBatches() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/meta/batches?project_id=${projectId}`);
      setBatches(r.data as BatchRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los lotes');
    } finally {
      setLoading(false);
    }
  }

  async function loadItems(batchId: string) {
    setError(null);
    try {
      const r = await api.get(`/meta/batches/${batchId}/items`);
      setItems(r.data as ItemRow[]);
      setSelectedBatchId(batchId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los items del lote');
    }
  }

  async function loadStudies() {
    if (!projectId) return;
    setError(null);
    try {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/studies?project_id=${projectId}${q}`);
      const nextStudies = r.data as StudyRow[];
      setStudies(nextStudies);
      if (!selectedStudyId && nextStudies[0]) {
        setSelectedStudyId(nextStudies[0].id);
      }
      if (selectedStudyId && !nextStudies.some((study) => study.id === selectedStudyId)) {
        setSelectedStudyId(nextStudies[0]?.id || null);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los estudios');
    }
  }

  async function loadExports() {
    if (!projectId) return;
    setError(null);
    try {
      const q = selectedBatchId ? `&batch_id=${selectedBatchId}` : '';
      const r = await api.get(`/meta/exports?project_id=${projectId}${q}`);
      setExportsList(r.data as ExportRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar las exportaciones');
    }
  }

  async function createBatch() {
    if (!projectId) return;
    if (!files || files.length === 0) {
      setError('Selecciona al menos 1 PDF');
      return;
    }

    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const form = new FormData();
      form.append('project_id', projectId);
      if (title.trim()) form.append('title', title.trim());
      Array.from(files).forEach((file) => form.append('files', file));

      const r = await api.post('/meta/batches', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const batchId = r.data?.batch_id as string;
      setNotice(`Lote creado: ${batchId} (job: ${r.data?.job_id})`);
      setFiles(null);
      setTitle('');
      await loadBatches();
      if (batchId) await loadItems(batchId);
      await loadStudies();
      await loadExports();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo crear el lote');
    } finally {
      setCreating(false);
    }
  }

  async function retryItem(itemId: string) {
    setError(null);
    setNotice(null);
    try {
      const r = await api.post(`/meta/items/${itemId}/retry`);
      setNotice(`Reintento encolado: job ${r.data?.job_id}`);
      if (selectedBatchId) await loadItems(selectedBatchId);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'El reintento fallo');
    }
  }

  async function exportExcel() {
    if (!projectId) return;
    setError(null);
    setNotice(null);
    try {
      const r = await api.post('/meta/export', {
        project_id: projectId,
        batch_id: selectedBatchId,
      });
      const jid = r.data?.job_id as string | undefined;
      if (jid) {
        setExportJobId(jid);
        setExportJobStatus({ status: 'queued', progress: 0, error: null });
      }
      setNotice(`Job de exportacion encolado: ${jid || '(job desconocido)'}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La exportacion fallo');
    } finally {
      await loadExports();
    }
  }

  async function downloadExport(row: ExportRow) {
    setError(null);
    try {
      const r = await api.get(`/meta/exports/${row.id}/download`, { responseType: 'blob' });
      downloadBlob(r.data as Blob, row.filename || 'exportacion_meta.xlsx');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La descarga fallo');
    }
  }

  useEffect(() => {
    void loadBatches();
    void loadStudies();
    void loadExports();
  }, [projectId]);

  useEffect(() => {
    void loadStudies();
    void loadExports();
  }, [selectedBatchId]);

  useEffect(() => {
    if (!selectedBatchId || runningItems.length === 0) return;
    const timer = window.setInterval(() => {
      void loadItems(selectedBatchId);
      void loadStudies();
    }, 4000);
    return () => window.clearInterval(timer);
  }, [selectedBatchId, runningItems.map((item) => item.id).join('|')]);

  useEffect(() => {
    if (!exportJobId) return;

    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${exportJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        setExportJobStatus({ status, progress, error: err });

        if (status === 'completed') {
          await loadExports();
          setExportJobId(null);
        }
        if (status === 'failed' || status === 'cancelled') {
          setExportJobId(null);
        }
      } catch (e: any) {
        setExportJobStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'La consulta del job fallo' });
      }
    }

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, 4000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [exportJobId]);

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Extracción estructurada</div>
          <h2>Convierte PDFs en estudios revisables</h2>
          <p>Sube lotes, sigue su procesamiento y revisa los estudios extraídos antes de exportar o analizar.</p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{batches.length} lotes</span>
          <span className="rc-discover-badge">{studies.length} estudios</span>
          <span className="rc-discover-badge">{runningItems.length} items activos</span>
          <span className="rc-discover-badge">{exportsList.length} exportaciones</span>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}
      {notice ? <div className="rc-product-card"><div className="rc-help">{notice}</div></div> : null}

      <div className="rc-product-two-column rc-product-two-column--wide" style={{ alignItems: 'start' }}>
        <div className="rc-stack">
          <div className="rc-product-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Cola de lotes</div>
                <div className="rc-help">Selecciona un lote para enfocarte en sus items y resultados de estudio.</div>
              </div>
              <button className="rc-btn rc-btn--subtle" onClick={() => void loadBatches()} disabled={loading}>
                {loading ? 'Actualizando...' : 'Actualizar'}
              </button>
            </div>
            <div style={{ height: 12 }} />
            {batches.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay lotes de extraccion</div>
                <div className="rc-help">Crea un lote con uno o mas PDFs para empezar a generar registros estructurados de estudio.</div>
              </div>
            ) : (
              <div className="rc-card-list">
                {batches.map((batch) => (
                  <button
                    key={batch.id}
                    onClick={() => void loadItems(batch.id)}
                    className={`rc-list-button ${batch.id === selectedBatchId ? 'rc-list-button--active' : ''}`}
                  >
                    <div className="rc-detail-header">
                      <div style={{ fontWeight: 850 }}>{batch.title || '(lote sin titulo)'}</div>
                      <span className={batch.status === 'completed' ? 'rc-badge rc-badge--success' : batch.status === 'failed' ? 'rc-badge rc-badge--danger' : 'rc-badge rc-badge--info'}>
                        {batch.status}
                      </span>
                    </div>
                    <div className="rc-help" style={{ marginTop: 8 }}>{formatDate(batch.created_at)}</div>
                  </button>
                ))}
              </div>
            )}
            <div style={{ height: 12 }} />
            <button className="rc-btn rc-btn--subtle" onClick={() => setSelectedBatchId(null)} disabled={!selectedBatchId}>
              Quitar foco del lote
            </button>
          </div>

          <div className="rc-product-card">
            <div className="rc-card-title">Nuevo lote de extraccion</div>
            <div className="rc-help" style={{ marginBottom: 12 }}>Elige los PDFs, nombra opcionalmente la corrida y deja que la cola de workers los procese en segundo plano.</div>
            <div className="rc-card-list">
              <div>
                <div className="rc-kicker">Titulo del lote</div>
                <input className="rc-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="ej. metaanalisis injerto ACL" />
              </div>
              <div>
                <div className="rc-kicker">Archivos PDF</div>
                <input type="file" multiple accept="application/pdf" onChange={(e) => setFiles(e.target.files)} />
                <div className="rc-help" style={{ marginTop: 8 }}>
                  {selectedFilesCount ? `${selectedFilesCount} archivo(s) seleccionados.` : 'Elige uno o mas PDFs.'} La extraccion se ejecuta de forma asincrona a traves de los workers de Redis.
                </div>
              </div>
              <button className="rc-btn rc-btn--primary" disabled={creating} onClick={createBatch}>
                {creating ? 'Creando...' : 'Crear y extraer'}
              </button>
            </div>
          </div>

          <div className="rc-product-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Exportaciones</div>
                <div className="rc-help">Empaqueta los datos actuales de extraccion para revision o analisis posterior.</div>
              </div>
              <button className="rc-btn rc-btn--subtle" onClick={() => void loadExports()}>Actualizar</button>
            </div>
            <div style={{ height: 12 }} />
              <button className="rc-btn rc-btn--primary" onClick={exportExcel} disabled={Boolean(exportJobId)}>
                {exportJobId ? 'Exportando...' : 'Exportar Excel'}
              </button>
            {exportJobStatus ? (
              <div className="rc-help" style={{ marginTop: 10 }}>
                Estado de exportacion: {exportJobStatus.status} · {exportJobStatus.progress}%
                {exportJobStatus.error ? ` · ${String(exportJobStatus.error)}` : ''}
              </div>
            ) : null}
            <div style={{ height: 12 }} />
            {exportsList.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay exportaciones</div>
                <div className="rc-help">Ejecuta una exportacion cuando un lote ya haya producido estudios.</div>
              </div>
            ) : (
              <div className="rc-card-list">
                {exportsList.map((item) => (
                  <div key={item.id} className="rc-soft-card">
                    <div className="rc-detail-header">
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.filename}</div>
                        <div className="rc-help" style={{ marginTop: 6 }}>{formatDate(item.created_at)}</div>
                      </div>
                      <button className="rc-btn rc-btn--subtle" onClick={() => void downloadExport(item)}>Descargar</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rc-stack">
          <div className="rc-product-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Items del lote</div>
                <div className="rc-help">
                  {selectedBatch ? `Siguiendo los articulos de "${selectedBatch.title || 'Lote sin titulo'}".` : 'Selecciona un lote para inspeccionar el progreso de sus items y sus fallos.'}
                </div>
              </div>
              {runningItems.length ? <span className="rc-badge rc-badge--info">Autoactualizando</span> : null}
            </div>
            <div style={{ height: 12 }} />
            {selectedBatchId ? (
              <>
                <div className="rc-metric-grid" style={{ marginBottom: 12 }}>
                  <div className="rc-metric-tile"><strong>{items.length}</strong><span>Items</span></div>
                  <div className="rc-metric-tile"><strong>{completedItems}</strong><span>Completados</span></div>
                  <div className="rc-metric-tile"><strong>{failedItems}</strong><span>Fallidos</span></div>
                </div>
                {items.length === 0 ? (
                  <div className="rc-empty-state">
                    <div style={{ fontWeight: 800, marginBottom: 6 }}>El lote todavia no tiene items</div>
                    <div className="rc-help">Es posible que los archivos sigan entrando a la cola. Revisa Tareas si los workers de Redis estan ocupados.</div>
                  </div>
                ) : (
                  <div className="rc-card-list">
                    {items.map((item) => (
                      <div key={item.id} className="rc-soft-card">
                        <div className="rc-detail-header">
                          <div style={{ flex: 1, minWidth: 220 }}>
                            <div style={{ fontWeight: 850 }}>{item.paper_title || item.paper_filename || 'Item sin titulo'}</div>
                            <div className="rc-help" style={{ marginTop: 8 }}>
                              {item.paper_filename ? `${item.paper_filename} · ` : ''}
                              paper_id {item.paper_id}
                            </div>
                          </div>
                          <span className={item.status === 'completed' ? 'rc-badge rc-badge--success' : item.status === 'failed' ? 'rc-badge rc-badge--danger' : 'rc-badge rc-badge--info'}>
                            {item.status}
                          </span>
                        </div>
                        {item.error_message ? <div className="rc-error" style={{ marginTop: 10 }}>{item.error_message}</div> : null}
                        <div className="rc-row" style={{ marginTop: 10 }}>
                          <button className="rc-btn" onClick={() => void retryItem(item.id)} disabled={['queued', 'started'].includes(item.status)}>
                            Reintentar item
                          </button>
                          {item.updated_at ? <div className="rc-help">Actualizado {formatDate(item.updated_at)}</div> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>No hay lote seleccionado</div>
                <div className="rc-help">Elige un lote de la cola para revisar el progreso de sus items, fallos y controles de reintento.</div>
              </div>
            )}
          </div>

          <div className="rc-product-card">
            <div className="rc-toolbar">
              <div>
                <div className="rc-card-title" style={{ marginBottom: 4 }}>Revision de estudios</div>
                <div className="rc-help">Explora los estudios extraidos y abre el visor detallado para revisar confianza, riesgo de sesgo y tamanos de efecto.</div>
              </div>
              <button className="rc-btn rc-btn--subtle" onClick={() => void loadStudies()}>Actualizar</button>
            </div>
            <div style={{ height: 12 }} />
            {studies.length === 0 ? (
              <div className="rc-empty-state">
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay estudios disponibles</div>
                <div className="rc-help">Los estudios aparecen aqui a medida que los items completan la extraccion. Cuando llegue uno, este panel se convierte en una vista dividida de revision.</div>
              </div>
            ) : (
              <div className="rc-split-layout">
                <div className="rc-card-list" style={{ maxHeight: 620, overflow: 'auto', paddingRight: 4 }}>
                  {studies.map((study) => (
                    <button
                      key={study.id}
                      onClick={() => setSelectedStudyId(study.id)}
                      className={`rc-list-button ${study.id === selectedStudyId ? 'rc-list-button--active' : ''}`}
                    >
                      <div className="rc-detail-header">
                        <div style={{ fontWeight: 850, fontSize: 13, lineHeight: 1.3 }}>
                          {study.paper_title || study.paper_filename || `Estudio ${study.id}`}
                        </div>
                        {study.rob_auto_generated ? <span className="rc-badge">ROB auto</span> : null}
                      </div>
                      <div className="rc-help" style={{ marginTop: 8 }}>
                        v{study.version} · confianza {study.extraction_confidence}
                        {study.batch_id ? ' · en lote' : ''}
                      </div>
                    </button>
                  ))}
                </div>

                <div>
                  {selectedStudyId ? (
                    <StudyViewer studyId={selectedStudyId} onSelectStudyId={setSelectedStudyId} />
                  ) : (
                    <div className="rc-empty-state">
                      <div style={{ fontWeight: 800, marginBottom: 6 }}>Selecciona un estudio</div>
                      <div className="rc-help">Elige un estudio de la columna izquierda para revisar la evidencia extraida en detalle.</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { useConfirm } from '../ui/Dialog/useConfirm';
import { useToast } from '../ui/Toast/ToastProvider';
import { Skeleton, SkeletonLines } from '../ui/Skeleton/Skeleton';

type JobRow = {
  id: string;
  job_type: string;
  status: string;
  progress_percent: number;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  result?: any;
};

function formatDate(value?: string | null) {
  if (!value) return 'Pendiente';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function JobsPage() {
  const confirm = useConfirm();
  const toast = useToast();

  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runningJobs = useMemo(
    () => jobs.filter((job) => ['queued', 'started', 'progress', 'retry_pending'].includes(job.status)),
    [jobs],
  );
  const failedJobs = useMemo(() => jobs.filter((job) => job.status === 'failed').length, [jobs]);
  const completedJobs = useMemo(() => jobs.filter((job) => job.status === 'completed').length, [jobs]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/jobs?limit=50');
      setJobs(response.data as JobRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los jobs');
    } finally {
      setLoading(false);
    }
  }

  async function pollJob(id: string) {
    setError(null);
    try {
      const response = await api.get(`/jobs/${id}`);
      const updated = response.data as Partial<JobRow>;
      setJobs((prev) => prev.map((job) => (job.id === id ? ({ ...job, ...updated } as JobRow) : job)));
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La consulta del job falló');
    }
  }

  async function cancel(id: string) {
    const ok = await confirm({
      title: '¿Cancelar este job?',
      body: 'Esto solicita la cancelación. Algunas tareas pueden seguir corriendo brevemente en segundo plano.',
      confirmText: 'Cancelar job',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.post(`/jobs/${id}/cancel`);
      toast.success('Cancelación solicitada', `Job ${id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La cancelación falló');
    }
  }

  async function retry(id: string) {
    setError(null);
    try {
      await api.post(`/jobs/${id}/retry`);
      toast.success('Reintento encolado', `Job ${id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'El reintento falló');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (runningJobs.length === 0) return;
    const timer = window.setInterval(() => {
      runningJobs.slice(0, 5).forEach((job) => {
        void pollJob(job.id);
      });
    }, 4000);
    return () => window.clearInterval(timer);
  }, [runningJobs.map((job) => job.id).join('|')]);

  return (
    <div className="rc-product-page">
      <div className="rc-product-page__header">
        <div>
          <div className="rc-kicker">Operaciones</div>
          <h2>Monitorea el trabajo en segundo plano</h2>
          <p>
            Aquí ves parseo, extracción, exportaciones y cualquier otra tarea asíncrona con estados honestos y polling real.
          </p>
        </div>
        <div className="rc-discover-badges">
          <span className="rc-discover-badge">{runningJobs.length} activos</span>
          <span className="rc-discover-badge">{failedJobs} fallidos</span>
          <span className="rc-discover-badge">{completedJobs} completados</span>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-product-card">
        <div className="rc-product-card__header">
          <div>
            <div className="rc-card-title">Salud de la cola</div>
            <div className="rc-help">
              {runningJobs.length
                ? 'Los jobs activos se consultan automáticamente. Si Redis o una cola fallan, lo verás reflejado aquí.'
                : 'No hay jobs activos ahora mismo.'}
            </div>
          </div>
          <button className="rc-btn rc-btn--subtle" onClick={() => void load()} disabled={loading}>
            {loading ? 'Actualizando…' : 'Actualizar cola'}
          </button>
        </div>
      </div>

      {loading && jobs.length === 0 ? (
        <div className="rc-product-card">
          <Skeleton height={14} width="35%" />
          <div style={{ height: 10 }} />
          <SkeletonLines lines={5} lineHeight={12} lastLineWidth="55%" />
        </div>
      ) : null}

      {!loading && jobs.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavía no hay jobs</div>
          <div className="rc-help">Los jobs aparecerán aquí cuando el sistema procese documentos, extracciones o exportaciones.</div>
        </div>
      ) : null}

      <div className="rc-discover-card-list">
        {jobs.map((job) => (
          <div key={job.id} className="rc-discover-result-card">
            <div className="rc-discover-result-card__header">
              <div style={{ flex: 1, minWidth: 240 }}>
                <h3 className="rc-discover-result-card__title" style={{ fontSize: 24 }}>{job.job_type}</h3>
                <div className="rc-discover-result-card__journal">ID del job {job.id}</div>
              </div>
              <div className="rc-discover-badges">
                <span className="rc-discover-badge">{job.status}</span>
                <span className="rc-discover-badge">{Math.max(0, Math.min(100, job.progress_percent || 0))}%</span>
              </div>
            </div>

            <div className="rc-product-job-grid">
              <div className="rc-product-job-stat"><strong>{formatDate(job.created_at)}</strong><span>Creado</span></div>
              <div className="rc-product-job-stat"><strong>{formatDate(job.started_at)}</strong><span>Iniciado</span></div>
              <div className="rc-product-job-stat"><strong>{formatDate(job.completed_at)}</strong><span>Completado</span></div>
            </div>

            <div className="rc-progress">
              <div style={{ width: `${Math.max(0, Math.min(100, job.progress_percent || 0))}%` }} />
            </div>

            {job.error ? <div className="rc-error">{job.error}</div> : null}

            <div className="rc-row">
              <button className="rc-btn rc-btn--subtle" onClick={() => void pollJob(job.id)}>
                Consultar ahora
              </button>
              {['queued', 'started', 'progress', 'retry_pending'].includes(job.status) ? (
                <button className="rc-btn rc-btn--subtle" onClick={() => void cancel(job.id)}>
                  Cancelar
                </button>
              ) : null}
              {['failed', 'retry_pending'].includes(job.status) ? (
                <button className="rc-btn rc-btn--primary" onClick={() => void retry(job.id)}>
                  Reintentar
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

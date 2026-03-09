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

function StatusPill({ status }: { status: string }) {
  const cls =
    status === 'completed'
      ? 'rc-badge rc-badge--success'
      : status === 'failed'
        ? 'rc-badge rc-badge--danger'
        : status === 'started' || status === 'progress'
          ? 'rc-badge rc-badge--info'
          : 'rc-badge';

  return <span className={cls}>{status}</span>;
}

export default function JobsPage() {
  const confirm = useConfirm();
  const toast = useToast();

  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runningJobs = useMemo(() => jobs.filter((job) => ['queued', 'started', 'progress'].includes(job.status)), [jobs]);
  const failedJobs = useMemo(() => jobs.filter((job) => job.status === 'failed').length, [jobs]);
  const completedJobs = useMemo(() => jobs.filter((job) => job.status === 'completed').length, [jobs]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/jobs?limit=50');
      setJobs(r.data as JobRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudieron cargar los jobs');
    } finally {
      setLoading(false);
    }
  }

  async function pollJob(id: string) {
    setError(null);
    try {
      const r = await api.get(`/jobs/${id}`);
      const updated = r.data as Partial<JobRow>;
      setJobs((prev) => prev.map((job) => (job.id === id ? { ...job, ...updated } as JobRow : job)));
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La consulta del job fallo');
    }
  }

  async function cancel(id: string) {
    const ok = await confirm({
      title: 'Cancelar este job?',
      body: 'Esto solicitara la cancelacion. Algunas tareas pueden seguir corriendo y no detenerse de inmediato.',
      confirmText: 'Cancelar job',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.post(`/jobs/${id}/cancel`);
      toast.success('Cancelacion solicitada', `Job ${id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'La cancelacion fallo');
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
    <div className="rc-section-shell">
      <div className="rc-hero-card">
        <div style={{ maxWidth: 760 }}>
          <div className="rc-pill">Operaciones</div>
          <h1 className="rc-page-title" style={{ marginTop: 12 }}>Tareas</h1>
          <div className="rc-subtitle">Monitorea el trabajo en segundo plano de parseo, extraccion, exportaciones y procesamiento documental desde una sola cola operativa.</div>
        </div>
        <div className="rc-metric-grid" style={{ minWidth: 320 }}>
          <div className="rc-metric-tile"><strong>{runningJobs.length}</strong><span>En ejecucion</span></div>
          <div className="rc-metric-tile"><strong>{failedJobs}</strong><span>Fallidos</span></div>
          <div className="rc-metric-tile"><strong>{completedJobs}</strong><span>Completados</span></div>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div className="rc-card">
        <div className="rc-toolbar">
          <div>
            <div className="rc-card-title" style={{ marginBottom: 4 }}>Salud de la cola</div>
            <div className="rc-help">{runningJobs.length ? 'Los jobs en ejecucion se consultan automaticamente cada pocos segundos.' : 'No hay jobs activos ahora mismo.'}</div>
          </div>
          <button className="rc-btn" onClick={() => void load()} disabled={loading}>
            {loading ? 'Actualizando...' : 'Actualizar cola'}
          </button>
        </div>
      </div>

      {loading && jobs.length === 0 ? (
        <div className="rc-card">
          <Skeleton height={14} width="35%" />
          <div style={{ height: 10 }} />
          <SkeletonLines lines={5} lineHeight={12} lastLineWidth="55%" />
        </div>
      ) : null}

      {!loading && jobs.length === 0 ? (
        <div className="rc-empty-state">
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Todavia no hay jobs</div>
          <div className="rc-help">Los jobs apareceran aqui cuando el espacio ejecute parseo, extraccion, exportaciones u otras tareas en segundo plano.</div>
        </div>
      ) : null}

      <div className="rc-card-list">
        {jobs.map((job) => (
          <div key={job.id} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="rc-detail-header">
              <div style={{ flex: 1, minWidth: 240 }}>
                <div style={{ fontWeight: 850, fontSize: 16 }}>{job.job_type}</div>
                <div className="rc-help" style={{ marginTop: 8 }}>ID del job {job.id}</div>
              </div>
              <StatusPill status={job.status} />
            </div>

            <div className="rc-metric-grid">
              <div className="rc-metric-tile">
                <strong>{Math.max(0, Math.min(100, job.progress_percent || 0))}%</strong>
                <span>Progreso</span>
              </div>
              <div className="rc-metric-tile">
                <strong>{formatDate(job.created_at)}</strong>
                <span>Creado</span>
              </div>
              <div className="rc-metric-tile">
                <strong>{formatDate(job.started_at)}</strong>
                <span>Iniciado</span>
              </div>
              <div className="rc-metric-tile">
                <strong>{formatDate(job.completed_at)}</strong>
                <span>Completado</span>
              </div>
            </div>

            <div>
              <div className="rc-progress">
                <div style={{ width: `${Math.max(0, Math.min(100, job.progress_percent || 0))}%` }} />
              </div>
            </div>

            {job.error ? <div className="rc-error">{job.error}</div> : null}

            <div className="rc-row">
              <button className="rc-btn" onClick={() => void pollJob(job.id)}>Consultar ahora</button>
              {['queued', 'started', 'progress'].includes(job.status) ? (
                <button className="rc-btn rc-btn--ghost" onClick={() => void cancel(job.id)}>
                  Cancelar
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

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

function StatusPill({ status }: { status: string }) {
  const cls =
    status === 'completed'
      ? 'rc-badge rc-badge--success'
      : status === 'failed'
        ? 'rc-badge rc-badge--danger'
        : status === 'started'
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

  const runningJobs = useMemo(
    () => jobs.filter((j) => ['queued', 'started', 'progress'].includes(j.status)),
    [jobs],
  );

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get('/jobs?limit=50');
      setJobs(r.data as JobRow[]);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  }

  async function pollJob(id: string) {
    setError(null);
    try {
      const r = await api.get(`/jobs/${id}`);
      const updated = r.data as Partial<JobRow>;
      setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...updated } as JobRow : j)));
    } catch (e: any) {
      // common in dev if Redis is off
      setError(e?.response?.data?.detail || 'Polling failed');
    }
  }

  async function cancel(id: string) {
    const ok = await confirm({
      title: 'Cancel this job?',
      body: 'This will request cancellation. Some tasks may already be running and cannot stop instantly.',
      confirmText: 'Cancel job',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.post(`/jobs/${id}/cancel`);
      toast.success('Cancel requested', `Job ${id}`);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Cancel failed');
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (runningJobs.length === 0) return;
    const t = window.setInterval(() => {
      // Poll up to 5 running jobs per tick to keep it light
      runningJobs.slice(0, 5).forEach((j) => pollJob(j.id));
    }, 4000);
    return () => window.clearInterval(t);
  }, [runningJobs.map((j) => j.id).join('|')]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Jobs</h1>
        <div className="rc-subtitle">Background work queue: search ingestion, document parsing, extraction, exports and legacy jobs.</div>
      </div>

      <div className="rc-row">
        <button className="rc-btn" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        {runningJobs.length ? <div className="rc-help">Auto-polling running jobs…</div> : null}
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading && jobs.length === 0 ? (
          <div className="rc-card">
            <Skeleton height={14} width="35%" />
            <div style={{ height: 10 }} />
            <SkeletonLines lines={4} lineHeight={12} lastLineWidth="55%" />
          </div>
        ) : null}
        {!loading && jobs.length === 0 ? <div className="rc-muted">No jobs yet.</div> : null}
        {jobs.map((j) => (
          <div key={j.id} className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
              <div style={{ fontWeight: 800 }}>{j.job_type}</div>
              <StatusPill status={j.status} />
            </div>

            <div className="rc-help">id: {j.id}</div>

            <div>
              <div className="rc-help">progress: {j.progress_percent || 0}%</div>
              <div className="rc-progress" style={{ marginTop: 6 }}>
                <div style={{ width: `${Math.max(0, Math.min(100, j.progress_percent || 0))}%` }} />
              </div>
            </div>

            {j.error ? <div className="rc-error" style={{ fontSize: 12 }}>{j.error}</div> : null}

            <div className="rc-row" style={{ marginTop: 2 }}>
              <button className="rc-btn" onClick={() => pollJob(j.id)}>Poll</button>
              {['queued', 'started', 'progress'].includes(j.status) ? (
                <button className="rc-btn rc-btn--ghost" onClick={() => cancel(j.id)}>
                  Cancel
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

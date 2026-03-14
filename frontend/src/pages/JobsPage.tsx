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

type TypeFilter = 'all' | string;

function statusBadge(status: string) {
  if (status === 'completed') return 'rc-badge rc-badge--success';
  if (status === 'failed') return 'rc-badge rc-badge--danger';
  if (status === 'started' || status === 'progress') return 'rc-badge rc-badge--info';
  return 'rc-badge';
}

function duration(j: JobRow): string {
  const start = j.started_at || j.created_at;
  const end = j.completed_at || ((['completed', 'failed'].includes(j.status)) ? null : new Date().toISOString());
  if (!start) return '\u2014';
  try {
    const ms = new Date(end || new Date().toISOString()).getTime() - new Date(start).getTime();
    if (ms < 1000) return '<1s';
    if (ms < 60000) return `${Math.round(ms / 1000)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
  } catch { return '\u2014'; }
}

function formatDate(iso?: string | null): string {
  if (!iso) return '\u2014';
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}

export default function JobsPage() {
  const confirm = useConfirm();
  const toast = useToast();

  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');

  const runningJobs = useMemo(
    () => jobs.filter(j => ['queued', 'started', 'progress'].includes(j.status)),
    [jobs],
  );

  const jobTypes = useMemo(() => {
    const types = new Set(jobs.map(j => j.job_type));
    return Array.from(types).sort();
  }, [jobs]);

  const filtered = useMemo(() => {
    if (typeFilter === 'all') return jobs;
    return jobs.filter(j => j.job_type === typeFilter);
  }, [jobs, typeFilter]);

  async function load() {
    setLoading(true); setError(null);
    try {
      const r = await api.get('/jobs?limit=50');
      setJobs(r.data as JobRow[]);
    } catch (e: any) { setError(e?.response?.data?.detail || 'Failed to load jobs'); }
    finally { setLoading(false); }
  }

  async function pollJob(id: string) {
    try {
      const r = await api.get(`/jobs/${id}`);
      const updated = r.data as Partial<JobRow>;
      setJobs(prev => prev.map(j => j.id === id ? { ...j, ...updated } as JobRow : j));
    } catch { /* ignore polling errors */ }
  }

  async function cancel(id: string) {
    const ok = await confirm({
      title: '\u00bfCancelar este job?',
      body: 'Se solicitar\u00e1 la cancelaci\u00f3n. Algunos tasks ya ejecut\u00e1ndose no pueden detenerse de inmediato.',
      confirmText: 'Cancel job',
      danger: true,
    });
    if (!ok) return;
    try {
      await api.post(`/jobs/${id}/cancel`);
      toast.success('Cancel requested', `Job ${id.slice(0, 8)}`);
      await load();
    } catch (e: any) { setError(e?.response?.data?.detail || 'Cancel failed'); }
  }

  useEffect(() => { load(); }, []);

  // Polling cada 3s si hay jobs activos
  useEffect(() => {
    if (runningJobs.length === 0) return;
    const t = window.setInterval(() => {
      runningJobs.slice(0, 5).forEach(j => pollJob(j.id));
    }, 3000);
    return () => window.clearInterval(t);
  }, [runningJobs.map(j => j.id).join('|')]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h1 className="rc-page-title">Jobs</h1>
        <div className="rc-subtitle">Background work queue: search ingestion, document parsing, extraction, exports and legacy jobs.</div>
      </div>

      <div className="rc-row" style={{ justifyContent: 'space-between' }}>
        <div className="rc-row" style={{ gap: 8 }}>
          <button className="rc-btn" onClick={load} disabled={loading} style={{ padding: '8px 12px', fontSize: 12 }}>
            {loading ? 'Loading\u2026' : 'Refresh'}
          </button>
          <select className="rc-input" style={{ width: 180, padding: '8px 10px', fontSize: 13 }} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
            <option value="all">All types</option>
            {jobTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          {runningJobs.length > 0 && (
            <span className="rc-badge rc-badge--info" style={{ fontSize: 11 }}>Auto-polling {runningJobs.length} active</span>
          )}
        </div>
        <span className="rc-help">{filtered.length} job{filtered.length !== 1 ? 's' : ''}</span>
      </div>

      {error && <div className="rc-error">{String(error)}</div>}

      {loading && jobs.length === 0 ? (
        <div className="rc-card">
          <Skeleton height={14} width="35%" />
          <div style={{ height: 10 }} />
          <SkeletonLines lines={4} lineHeight={12} lastLineWidth="55%" />
        </div>
      ) : null}

      {!loading && jobs.length === 0 ? (
        <div className="rc-card" style={{ textAlign: 'center', padding: '56px 24px' }}>
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" style={{ margin: '0 auto 16px', display: 'block' }}>
            <circle cx="40" cy="40" r="30" fill="rgba(245,158,11,0.07)" stroke="rgba(245,158,11,0.2)" strokeWidth="1.5"/>
            <circle cx="40" cy="40" r="20" fill="rgba(245,158,11,0.06)" stroke="rgba(245,158,11,0.18)" strokeWidth="1.5"/>
            <circle cx="40" cy="40" r="6" fill="rgba(245,158,11,0.2)" stroke="rgba(245,158,11,0.4)" strokeWidth="1.5"/>
            <line x1="40" y1="10" x2="40" y2="20" stroke="rgba(245,158,11,0.35)" strokeWidth="2" strokeLinecap="round"/>
            <line x1="40" y1="60" x2="40" y2="70" stroke="rgba(245,158,11,0.35)" strokeWidth="2" strokeLinecap="round"/>
            <line x1="10" y1="40" x2="20" y2="40" stroke="rgba(245,158,11,0.35)" strokeWidth="2" strokeLinecap="round"/>
            <line x1="60" y1="40" x2="70" y2="40" stroke="rgba(245,158,11,0.35)" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          <div style={{ fontWeight: 700, fontSize: 15, fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}>No jobs yet</div>
          <div className="rc-help" style={{ marginTop: 6 }}>Background jobs appear here when you process papers, run searches, or generate reports.</div>
        </div>
      ) : null}

      {filtered.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--rc-border)', textAlign: 'left' }}>
                <th style={{ padding: '8px 6px' }}>Type</th>
                <th style={{ padding: '8px 6px', width: 100 }}>Status</th>
                <th style={{ padding: '8px 6px', width: 120 }}>Progress</th>
                <th style={{ padding: '8px 6px', width: 120 }}>Started</th>
                <th style={{ padding: '8px 6px', width: 80 }}>Duration</th>
                <th style={{ padding: '8px 6px', width: 120 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(j => (
                <tr key={j.id} style={{ borderBottom: '1px solid var(--rc-border)' }}>
                  <td style={{ padding: '8px 6px' }}>
                    <div style={{ fontWeight: 700 }}>{j.job_type}</div>
                    <div className="rc-help" style={{ fontSize: 10 }}>{j.id.slice(0, 8)}</div>
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    <span className={statusBadge(j.status)} style={{ fontSize: 11 }}>{j.status}</span>
                  </td>
                  <td style={{ padding: '8px 6px' }}>
                    <div className="rc-progress" style={{ height: 6 }}>
                      <div style={{ width: `${Math.max(0, Math.min(100, j.progress_percent || 0))}%` }} />
                    </div>
                    <div className="rc-help" style={{ fontSize: 10, marginTop: 2 }}>{j.progress_percent || 0}%</div>
                  </td>
                  <td style={{ padding: '8px 6px', fontSize: 12 }}>{formatDate(j.started_at || j.created_at)}</td>
                  <td style={{ padding: '8px 6px', fontSize: 12, fontFamily: 'monospace' }}>{duration(j)}</td>
                  <td style={{ padding: '8px 6px' }}>
                    <div className="rc-row" style={{ gap: 4 }}>
                      <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11 }} onClick={() => pollJob(j.id)}>Poll</button>
                      {['queued', 'started', 'progress'].includes(j.status) && (
                        <button className="rc-btn" style={{ padding: '4px 8px', fontSize: 11, color: 'var(--rc-danger)' }} onClick={() => cancel(j.id)}>Cancel</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.some(j => j.error) && (
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {filtered.filter(j => j.error).map(j => (
                <div key={j.id} className="rc-error" style={{ fontSize: 11, padding: '6px 10px', background: 'rgba(185,28,28,0.06)', borderRadius: 8 }}>
                  <b>{j.job_type} ({j.id.slice(0, 8)}):</b> {j.error}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

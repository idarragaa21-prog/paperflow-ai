import { useEffect, useState, useRef, useCallback } from 'react';
import { api } from '../services/api';

export type JobStatus = {
  status: string;
  progress: number;
  error?: string | null;
  output?: Record<string, unknown>;
  result?: Record<string, unknown>;
};

type UseJobPollingOptions = {
  intervalMs?: number;
  onCompleted?: (status: JobStatus) => void;
  onFailed?: (status: JobStatus) => void;
};

/**
 * Polls a background job until it completes or fails.
 * Extracted from the duplicated polling pattern across ProjectLayout,
 * ClinicalPage, MetaPage, PapersPage, etc.
 */
export function useJobPolling(jobId: string | null, options: UseJobPollingOptions = {}) {
  const { intervalMs = 2000, onCompleted, onFailed } = options;
  const [status, setStatus] = useState<JobStatus | null>(null);
  const stoppedRef = useRef(false);

  const reset = useCallback(() => {
    setStatus(null);
  }, []);

  useEffect(() => {
    if (!jobId) {
      setStatus(null);
      return;
    }

    stoppedRef.current = false;

    async function poll() {
      if (stoppedRef.current) return;
      try {
        const r = await api.get(`/jobs/${jobId}`);
        const data = r.data as Record<string, unknown>;
        const s = String(data?.status || 'unknown');
        const progress = Number(data?.progress_percent || 0);
        const err = (data?.error as string) || null;
        const result = (data?.result as Record<string, unknown>) || {};
        const output = (result?.output as Record<string, unknown>) || (result?.rq_result as Record<string, unknown>)?.['output'] as Record<string, unknown>;

        const next: JobStatus = { status: s, progress, error: err, output, result };
        setStatus(next);

        if (s === 'completed') {
          onCompleted?.(next);
          return;
        }
        if (s === 'failed') {
          onFailed?.(next);
          return;
        }
      } catch (e: unknown) {
        const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || (e as Error)?.message || 'Polling failed';
        setStatus({ status: 'polling_error', progress: 0, error: msg });
      }
    }

    poll();
    const t = window.setInterval(poll, intervalMs);
    return () => {
      stoppedRef.current = true;
      window.clearInterval(t);
    };
  }, [jobId, intervalMs, onCompleted, onFailed]);

  const isRunning = !!jobId && !!status && !['completed', 'failed', 'polling_error'].includes(status.status);
  const isDone = status?.status === 'completed';
  const isFailed = status?.status === 'failed' || status?.status === 'polling_error';

  return { status, isRunning, isDone, isFailed, reset };
}

import { useEffect, useState } from 'react';
import { api } from '../services/api';

export type BatchJob = {
  status: string;
  progress: number;
  error?: string | null;
  output?: any;
};

export type UseBatchDownloadReturn = {
  batchJobId: string | null;
  batchJob: BatchJob | null;
  batchModalOpen: boolean;
  setBatchModalOpen: (v: boolean) => void;
  resetBatch: () => void;
  startBatchDownload: (
    projectId: string,
    papers: Array<{ pmid?: string; pmcid?: string; doi?: string; title: string; oa_url?: string }>,
    onError: (msg: string) => void,
  ) => Promise<void>;
  cancelBatch: () => Promise<void>;
};

export function useBatchDownload(): UseBatchDownloadReturn {
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [batchJob, setBatchJob] = useState<BatchJob | null>(null);
  const [batchModalOpen, setBatchModalOpen] = useState(false);

  // Poll while modal is open and job isn't terminal
  useEffect(() => {
    if (!batchJobId || !batchModalOpen) return;
    let alive = true;
    let t: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const r = await api.get(`/jobs/${batchJobId}`);
        const status = String(r.data?.status || 'queued');
        const progress = Number(r.data?.progress_percent || 0);
        const error = r.data?.error || null;
        const result = r.data?.result || {};
        const output = result?.output || result?.rq_result?.output;
        if (alive) setBatchJob({ status, progress, error, output });
        if (status === 'completed' || status === 'failed') return;
      } catch (e: any) {
        if (alive) setBatchJob((prev) => prev ?? { status: 'queued', progress: 0, error: e?.message || 'Poll failed' });
      }
      t = setTimeout(poll, 1000);
    }

    poll();
    return () => { alive = false; if (t) clearTimeout(t); };
  }, [batchJobId, batchModalOpen]);

  async function startBatchDownload(
    projectId: string,
    papers: Array<{ pmid?: string; pmcid?: string; doi?: string; title: string; oa_url?: string }>,
    onError: (msg: string) => void,
  ) {
    try {
      const resp = await api.post('/papers/batch-download', { project_id: projectId, papers });
      const jid = String(resp.data?.job_id || '');
      setBatchJobId(jid);
      setBatchJob({ status: 'queued', progress: 0, error: null });
      setBatchModalOpen(true);
    } catch (e: any) {
      onError(e?.response?.data?.detail || 'Batch download failed');
    }
  }

  async function cancelBatch() {
    if (!batchJobId) return;
    try { await api.post(`/jobs/${batchJobId}/cancel`); } catch { /* ignore */ }
  }

  function resetBatch() {
    setBatchJobId(null);
    setBatchJob(null);
    setBatchModalOpen(false);
  }

  return {
    batchJobId, batchJob,
    batchModalOpen, setBatchModalOpen,
    resetBatch, startBatchDownload, cancelBatch,
  };
}

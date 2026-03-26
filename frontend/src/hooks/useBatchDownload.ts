import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { BatchDownloadOutput, BatchDownloadTraceItem } from '../types/api';

export type BatchJob = {
  status: string;
  progress: number;
  error?: string | null;
  output?: BatchDownloadOutput | null;
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

function normalizeItem(item: unknown): BatchDownloadTraceItem {
  const raw = (item as Record<string, unknown>) || {};
  const status = raw.final_status;
  return {
    title: String(raw.title || 'Paper'),
    pmid: raw.pmid ? String(raw.pmid) : null,
    pmcid: raw.pmcid ? String(raw.pmcid) : null,
    doi: raw.doi ? String(raw.doi) : null,
    paper_id: raw.paper_id ? String(raw.paper_id) : null,
    source_provider: raw.source_provider ? String(raw.source_provider) : null,
    oa_url: raw.oa_url ? String(raw.oa_url) : null,
    landing_url: raw.landing_url ? String(raw.landing_url) : null,
    resolved_url: raw.resolved_url ? String(raw.resolved_url) : null,
    used_fallback: Boolean(raw.used_fallback),
    final_status:
      status === 'downloaded' || status === 'existing' || status === 'unavailable' || status === 'failed'
        ? status
        : 'failed',
    failure_reason: raw.failure_reason ? String(raw.failure_reason) : null,
  };
}

function normalizeItems(items: unknown): BatchDownloadTraceItem[] {
  if (!Array.isArray(items)) return [];
  return items.map((item) => normalizeItem(item));
}

function normalizeOutput(output: unknown): BatchDownloadOutput {
  const raw = ((output as Record<string, unknown>) || {}) as Record<string, unknown>;
  const downloaded = normalizeItems(raw.downloaded);
  const alreadyExists = normalizeItems(raw.already_exists);
  const notAvailable = normalizeItems(raw.not_available);
  const failed = normalizeItems(raw.failed);
  const items = normalizeItems(raw.items);
  return {
    items: items.length ? items : [...downloaded, ...alreadyExists, ...notAvailable, ...failed],
    downloaded,
    already_exists: alreadyExists,
    not_available: notAvailable,
    failed,
  };
}

function batchErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    if (detail) return detail;
  }
  return error instanceof Error ? error.message : fallback;
}

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
        const output = normalizeOutput(result?.output || result?.rq_result?.output);
        if (alive) setBatchJob({ status, progress, error, output });
        if (status === 'completed' || status === 'failed') return;
      } catch (error: unknown) {
        if (alive) {
          setBatchJob((prev) => prev ?? { status: 'queued', progress: 0, error: batchErrorMessage(error, 'Poll failed') });
        }
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
    } catch (error: unknown) {
      onError(batchErrorMessage(error, 'Batch download failed'));
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

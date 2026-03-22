import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { useConfirm } from '../../ui/Dialog/useConfirm';
import { useToast } from '../../ui/Toast/ToastProvider';
import EffectSizesGrid, { type EffectSize } from './EffectSizesGrid';
import RiskOfBiasGrid, { type RiskOfBiasRow } from './RiskOfBiasGrid';

export type StudyDetail = {
  id: string;
  project_id: string;
  paper_id: string;
  batch_id?: string | null;
  version: number;
  is_current: boolean;
  extraction_confidence: number;
  study_json: any;
  effects: EffectSize[];
  risk_of_bias: RiskOfBiasRow[];
};

type StudyVersionRow = {
  id: string;
  version: number;
  is_current: boolean;
  created_at?: string | null;
};

export default function StudyViewer({
  studyId,
  onSelectStudyId,
}: {
  studyId: string;
  onSelectStudyId?: (id: string) => void;
}) {
  const confirm = useConfirm();
  const toast = useToast();

  const [tab, setTab] = useState<'effects' | 'rob' | 'json'>('effects');
  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [versions, setVersions] = useState<StudyVersionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/meta/studies/${studyId}`);
      setStudy(r.data as StudyDetail);

      // Versions list (best-effort)
      try {
        const v = await api.get(`/meta/studies/${studyId}/versions`);
        setVersions(v.data as StudyVersionRow[]);
      } catch {
        setVersions([]);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load study');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [studyId]);

  const [reextractJobId, setReextractJobId] = useState<string | null>(null);
  const [reextractStatus, setReextractStatus] = useState<{ status: string; progress: number; error?: string | null } | null>(null);

  async function reextract() {
    const ok = await confirm({
      title: 'Re-extract this paper?',
      body: 'This will create a NEW version. Existing versions remain available.',
      confirmText: 'Re-extract',
    });
    if (!ok) return;

    setError(null);
    try {
      const r = await api.post(`/meta/studies/${studyId}/re-extract`);
      const jid = r.data?.job_id as string | undefined;
      if (jid) {
        setReextractJobId(jid);
        setReextractStatus({ status: 'queued', progress: 0, error: null });
      }
      toast.success('Job enqueued', `Re-extract: ${jid || '(unknown job id)'}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to enqueue re-extract');
    }
  }

  // Poll re-extract job
  useEffect(() => {
    if (!reextractJobId) return;

    let stopped = false;

    async function poll() {
      if (stopped) return;
      try {
        const r = await api.get(`/jobs/${reextractJobId}`);
        const status = String((r.data as any)?.status || 'unknown');
        const progress = Number((r.data as any)?.progress_percent || 0);
        const err = (r.data as any)?.error || null;
        setReextractStatus({ status, progress, error: err });

        if (status === 'completed') {
          // Reload and auto-jump to current version if it changed
          await load();
          try {
            const v = await api.get(`/meta/studies/${studyId}/versions`);
            const rows = (v.data as StudyVersionRow[]) || [];
            const cur = rows.find((x) => x.is_current) || rows[0];
            if (cur && cur.id && cur.id !== studyId) onSelectStudyId?.(cur.id);
          } catch {
            // ignore
          }
          setReextractJobId(null);
        }
        if (status === 'failed') {
          setReextractJobId(null);
        }
      } catch (e: any) {
        setReextractStatus({ status: 'polling_error', progress: 0, error: e?.response?.data?.detail || 'Polling failed' });
      }
    }

    poll();
    const t = window.setInterval(poll, 4000);
    return () => {
      stopped = true;
      window.clearInterval(t);
    };
  }, [reextractJobId]);

  if (loading && !study) return <div>Loading study…</div>;
  if (error) return <div className="rc-error">{String(error)}</div>;
  if (!study) return <div>Select a study.</div>;

  const sj = (study.study_json || {}) as any;
  const title = String(sj.title || '(untitled)');
  const authors = String(sj.authors || sj.first_author || 'Not reported');
  const year = sj.year != null ? String(sj.year) : '—';
  const journal = String(sj.journal || '—');
  const design = String(sj.study_design || 'not_reported');
  const arms = Array.isArray(sj.arms) ? sj.arms : [];
  const outcomes = Array.isArray(sj.outcomes) ? sj.outcomes : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ minWidth: 280 }}>
          <div style={{ fontWeight: 900, fontSize: 16 }}>{title}</div>
          <div style={{ fontSize: 12, opacity: 0.78 }}>
            {authors} · {year} · {journal}
          </div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>
            design: <span style={{ fontWeight: 700 }}>{design}</span> · version {study.version} {study.is_current ? '(current)' : ''} · confidence{' '}
            {study.extraction_confidence}
          </div>
          <div style={{ fontSize: 11, opacity: 0.55 }}>study_id: {study.id}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
          <button onClick={reextract} disabled={Boolean(reextractJobId)}>
            {reextractJobId ? 'Re-extracting…' : 'Re-extract'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 10 }}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Arms</div>
          {arms.length === 0 ? <div style={{ opacity: 0.7 }}>No arms extracted.</div> : null}
          {arms.slice(0, 6).map((a: any, idx: number) => {
            const nRand = a.n_randomized;
            const nAna = a.n_analyzed;
            const impossible = nRand != null && nAna != null && Number(nAna) > Number(nRand);
            return (
              <div key={idx} style={{ padding: '6px 0', borderTop: idx ? '1px solid rgba(0,0,0,0.08)' : 'none' }}>
                <div style={{ fontWeight: 700 }}>{String(a.arm_name || `Arm ${idx + 1}`)}</div>
                {a.intervention_description ? <div style={{ fontSize: 12, opacity: 0.78 }}>{String(a.intervention_description)}</div> : null}
                <div style={{ fontSize: 12, opacity: 0.7, color: impossible ? 'crimson' : 'inherit' }}>
                  n_randomized: {nRand ?? '—'} · n_analyzed: {nAna ?? '—'}
                  {impossible ? <span style={{ marginLeft: 8, fontWeight: 700 }}>(impossible: analyzed &gt; randomized)</span> : null}
                </div>
              </div>
            );
          })}
          {arms.length > 6 ? <div style={{ fontSize: 12, opacity: 0.6 }}>+{arms.length - 6} more…</div> : null}
        </div>

        <div style={{ border: '1px solid rgba(0,0,0,0.12)', borderRadius: 10, padding: 10 }}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>Outcomes</div>
          {outcomes.length === 0 ? <div style={{ opacity: 0.7 }}>No outcomes extracted.</div> : null}
          {outcomes.slice(0, 10).map((o: any, idx: number) => (
            <div key={idx} style={{ padding: '6px 0', borderTop: idx ? '1px solid rgba(0,0,0,0.08)' : 'none' }}>
              <div style={{ fontWeight: 700 }}>{String(o.outcome_name || `Outcome ${idx + 1}`)}</div>
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                type: {String(o.outcome_type || '—')} {o.timepoint ? `· timepoint: ${String(o.timepoint)}` : ''}
              </div>
              {o.definition ? <div style={{ fontSize: 12, opacity: 0.7 }}>{String(o.definition)}</div> : null}
            </div>
          ))}
          {outcomes.length > 10 ? <div style={{ fontSize: 12, opacity: 0.6 }}>+{outcomes.length - 10} more…</div> : null}
        </div>
      </div>

      {versions.length ? (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Versions:</div>
          {versions.map((v) => (
            <button
              key={v.id}
              onClick={() => onSelectStudyId?.(v.id)}
              disabled={!onSelectStudyId || v.id === studyId}
              style={{
                fontSize: 12,
                padding: '3px 8px',
                borderRadius: 999,
                border: '1px solid rgba(0,0,0,0.18)',
                background: v.is_current ? 'rgba(16,185,129,0.14)' : 'rgba(0,0,0,0.04)',
              }}
            >
              v{v.version}{v.is_current ? ' (current)' : ''}
            </button>
          ))}
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button onClick={() => setTab('effects')} disabled={tab === 'effects'}>
          Effect sizes
        </button>
        <button onClick={() => setTab('rob')} disabled={tab === 'rob'}>
          Risk of bias
        </button>
        <button onClick={() => setTab('json')} disabled={tab === 'json'}>
          Raw JSON
        </button>
        {reextractStatus ? (
          <div style={{ fontSize: 12, opacity: 0.75 }}>
            re-extract: {reextractStatus.status} · {reextractStatus.progress}%
            {reextractStatus.error ? <span className="rc-error"> · {String(reextractStatus.error)}</span> : null}
          </div>
        ) : null}
      </div>

      {tab === 'effects' ? <EffectSizesGrid studyId={study.id} effects={study.effects} onChanged={load} /> : null}
      {tab === 'rob' ? <RiskOfBiasGrid studyId={study.id} rows={study.risk_of_bias} onChanged={load} /> : null}
      {tab === 'json' ? (
        <pre
          style={{
            margin: 0,
            whiteSpace: 'pre-wrap',
            background: 'rgba(0,0,0,0.04)',
            borderRadius: 10,
            padding: 12,
          }}
        >
          {JSON.stringify(study.study_json, null, 2)}
        </pre>
      ) : null}

      <div style={{ fontSize: 12, opacity: 0.7 }}>
        Tip: usually you want to edit the current version. Older versions are read-only by convention (we don't enforce it yet).
      </div>
    </div>
  );
}

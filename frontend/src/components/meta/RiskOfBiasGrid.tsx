import { useMemo, useState } from 'react';
import { api } from '../../services/api';

export type RiskOfBiasRow = {
  id: string;
  tool: string;
  domain: string;
  judgement: string;
  support_text?: string | null;
  auto_generated?: boolean;
};

export default function RiskOfBiasGrid({
  studyId,
  rows,
  onChanged,
}: {
  studyId: string;
  rows: RiskOfBiasRow[];
  onChanged?: () => Promise<void> | void;
}) {
  const [drafts, setDrafts] = useState<Record<string, Partial<RiskOfBiasRow>>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const merged = useMemo(() => {
    return rows.map((r) => ({ ...r, ...(drafts[r.id] || {}) }));
  }, [rows, drafts]);

  function setField(id: string, key: keyof RiskOfBiasRow, value: any) {
    setDrafts((prev) => {
      const next = { ...prev };
      const cur = { ...(next[id] || {}) };
      cur[key] = value;
      next[id] = cur;
      return next;
    });
  }

  async function saveRow(id: string) {
    const patchObj = drafts[id];
    if (!patchObj || Object.keys(patchObj).length === 0) return;

    setSaving(true);
    setError(null);
    try {
      await api.patch(`/meta/studies/${studyId}/rob/${id}`, patchObj);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      await onChanged?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to patch ROB');
    } finally {
      setSaving(false);
    }
  }

  async function addRob() {
    setError(null);
    setSaving(true);
    try {
      await api.post(`/meta/studies/${studyId}/rob`, {
        domain: 'randomization',
        tool: 'ROB2',
        judgement: 'unclear',
        support_text: '',
      });
      await onChanged?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add ROB');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 800 }}>Risk of bias</div>
        <button onClick={addRob} disabled={saving}>
          Add domain
        </button>
      </div>
      {error ? <div style={{ color: 'crimson' }}>{String(error)}</div> : null}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {rows.length === 0 ? <div style={{ opacity: 0.75 }}>No ROB rows yet. Click “Add domain”.</div> : null}
        {merged.map((r) => {
          const dirty = Boolean(drafts[r.id] && Object.keys(drafts[r.id]!).length);
          return (
            <div
              key={r.id}
              style={{
                border: '1px solid rgba(0,0,0,0.12)',
                borderRadius: 10,
                padding: 12,
                display: 'grid',
                gridTemplateColumns: '1fr 220px',
                gap: 10,
                background: dirty ? 'rgba(0,0,0,0.02)' : 'transparent',
              }}
            >
              <div>
                <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span>
                    {r.tool}: {r.domain}
                  </span>
                  {r.auto_generated ? (
                    <span
                      style={{
                        fontSize: 11,
                        padding: '2px 8px',
                        borderRadius: 999,
                        border: '1px solid rgba(245, 158, 11, 0.45)',
                        background: 'rgba(245, 158, 11, 0.12)',
                      }}
                    >
                      Auto-generated
                    </span>
                  ) : null}
                </div>
                <textarea
                  value={r.support_text || ''}
                  onChange={(e) => setField(r.id, 'support_text', e.target.value)}
                  placeholder="Support text (quote/summary from paper)…"
                  style={{ width: '100%', minHeight: 64, marginTop: 6 }}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <select value={r.judgement} onChange={(e) => setField(r.id, 'judgement', e.target.value)}>
                  <option value="low">low</option>
                  <option value="some_concerns">some_concerns</option>
                  <option value="high">high</option>
                  <option value="unclear">unclear</option>
                </select>
                <button disabled={saving || !dirty} onClick={() => saveRow(r.id)}>
                  {saving ? 'Saving…' : 'Save'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

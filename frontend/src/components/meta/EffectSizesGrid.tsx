import { useMemo, useState } from 'react';
import { api } from '../../services/api';
import { calcORFrom2x2 } from './effectMath';

export type EffectSize = {
  id: string;
  outcome_name: string;
  timepoint?: string | null;
  arm_intervention: string;
  arm_control: string;
  effect_measure: string;

  a_events?: number | null;
  b_non_events?: number | null;
  c_events?: number | null;
  d_non_events?: number | null;

  or_value?: number | null;
  log_or?: number | null;
  se_log_or?: number | null;
  ci_lower_95?: number | null;
  ci_upper_95?: number | null;

  adjusted_or?: number | null;
  adjusted_rr?: number | null;
  adjusted_hr?: number | null;
  adjustment_variables?: string | null;
  is_adjusted?: boolean;

  raw_extracted_value?: string | null;
  source_type?: string | null;
  source_page?: number | null;
  confidence?: number | null;
  comments?: string | null;
};

type DraftPatch = Partial<EffectSize>;

function numOrNull(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  if (!Number.isFinite(n)) return null;
  return n;
}

function intOrNull(s: string): number | null {
  const n = numOrNull(s);
  if (n === null) return null;
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function approxEq(a: any, b: any, tol = 1e-9): boolean {
  if (a === b) return true;
  if (a === null || a === undefined || b === null || b === undefined) return false;
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= tol;
  return false;
}

import { useConfirm } from '../../ui/Dialog/useConfirm';

export default function EffectSizesGrid({
  studyId,
  effects,
  onChanged,
}: {
  studyId: string;
  effects: EffectSize[];
  onChanged?: () => Promise<void> | void;
}) {
  const confirm = useConfirm();

  const [drafts, setDrafts] = useState<Record<string, DraftPatch>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const merged = useMemo(() => {
    return effects.map((e) => ({ ...e, ...(drafts[e.id] || {}) }));
  }, [effects, drafts]);

  const dirtyIds = useMemo(() => {
    return Object.entries(drafts)
      .filter(([, patch]) => Object.keys(patch).length > 0)
      .map(([id]) => id);
  }, [drafts]);

  function setField(effectId: string, key: keyof EffectSize, value: any) {
    setDrafts((prev) => {
      const next = { ...prev };
      const cur = { ...(next[effectId] || {}) };

      // Normalize empty strings
      if (value === '') value = null;

      cur[key] = value;
      next[effectId] = cur;
      return next;
    });
  }

  function clearDraft(effectId: string) {
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[effectId];
      return next;
    });
  }

  async function saveAll() {
    const updates: any[] = [];

    for (const id of dirtyIds) {
      const base = effects.find((e) => e.id === id);
      const patch = drafts[id];
      if (!base || !patch) continue;

      const patchKeys = Object.keys(patch);
      if (patchKeys.length === 0) continue;

      const has2x2Edit = ['a_events', 'b_non_events', 'c_events', 'd_non_events'].some((k) => patchKeys.includes(k));

      const mergedRow: EffectSize = { ...base, ...patch };

      const patchOut: any = { ...patch };

      // Basic sanity checks for 2x2 counts
      const counts = [mergedRow.a_events, mergedRow.b_non_events, mergedRow.c_events, mergedRow.d_non_events];
      if (counts.some((v) => v != null && Number(v) < 0)) {
        setError('Invalid 2x2 counts: negative values are not allowed.');
        return;
      }

      // If user edited 2x2 and effect_measure is OR-like, compute derived OR/CI deterministically.
      if (has2x2Edit && String(mergedRow.effect_measure || 'OR').toUpperCase() === 'OR') {
        const calc = calcORFrom2x2({
          a_events: mergedRow.a_events ?? null,
          b_non_events: mergedRow.b_non_events ?? null,
          c_events: mergedRow.c_events ?? null,
          d_non_events: mergedRow.d_non_events ?? null,
        });
        if (calc.ok) {
          patchOut.or_value = calc.or_value;
          patchOut.log_or = calc.log_or;
          patchOut.se_log_or = calc.se_log_or;
          patchOut.ci_lower_95 = calc.ci_lower_95;
          patchOut.ci_upper_95 = calc.ci_upper_95;
        }
      }

      updates.push({ id, patch: patchOut });
    }

    if (updates.length === 0) return;

    setSaving(true);
    setError(null);
    try {
      await api.patch(`/meta/studies/${studyId}/effects`, { updates });
      setDrafts({});
      await onChanged?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function addEffect() {
    setError(null);
    try {
      await api.post(`/meta/studies/${studyId}/effects`, {
        outcome_name: 'Outcome',
        arm_intervention: 'Intervention',
        arm_control: 'Control',
        effect_measure: 'OR',
      });
      await onChanged?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add effect');
    }
  }

  async function deleteEffect(effectId: string) {
    const ok = await confirm({
      title: 'Delete effect size row?',
      body: 'This will permanently remove the row from the study.' ,
      confirmText: 'Delete',
      danger: true,
    });
    if (!ok) return;

    setError(null);
    try {
      await api.delete(`/meta/studies/${studyId}/effects/${effectId}`);
      await onChanged?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to delete effect');
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <div style={{ fontWeight: 800 }}>Effect sizes</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={addEffect}>Add</button>
          <button disabled={saving || dirtyIds.length === 0} onClick={saveAll}>
            {saving ? 'Saving…' : `Save (${dirtyIds.length})`}
          </button>
        </div>
      </div>

      {error ? <div className="rc-error">{String(error)}</div> : null}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 1900 }}>
          <thead>
            <tr>
              {[
                'Outcome',
                'Timepoint',
                'Intervention arm',
                'Control arm',
                'Measure',
                'a',
                'b',
                'c',
                'd',
                'OR (calc)',
                '95% CI (calc)',
                'Adjusted?',
                'Adj OR',
                'Adj RR',
                'Adj HR',
                'Adjust vars',
                'Raw extracted',
                'Source type',
                'Source page',
                'Confidence',
                'Comments',
                '',
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: 'left',
                    fontSize: 12,
                    opacity: 0.85,
                    padding: '6px 8px',
                    borderBottom: '1px solid rgba(0,0,0,0.12)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {merged.map((row) => {
              const base = effects.find((e) => e.id === row.id) as EffectSize;
              const patch = drafts[row.id] || {};

              const calc = calcORFrom2x2({
                a_events: row.a_events ?? null,
                b_non_events: row.b_non_events ?? null,
                c_events: row.c_events ?? null,
                d_non_events: row.d_non_events ?? null,
              });

              const dirty = Object.keys(patch).length > 0;

              const showOr = calc.ok ? calc.or_value : null;
              const showCi = calc.ok ? [calc.ci_lower_95, calc.ci_upper_95] : null;

              const mismatchOr = calc.ok && base?.or_value != null && !approxEq(base.or_value, calc.or_value);

              const invalidCounts = [row.a_events, row.b_non_events, row.c_events, row.d_non_events].some(
                (v) => v != null && Number(v) < 0,
              );
              const hasZeros = [row.a_events, row.b_non_events, row.c_events, row.d_non_events].some((v) => v === 0);

              function cellStyle(changed: boolean, danger: boolean = false) {
                return {
                  padding: '6px 8px',
                  borderBottom: '1px solid rgba(0,0,0,0.08)',
                  background: danger
                    ? 'rgba(220,38,38,0.12)'
                    : changed
                      ? 'rgba(99, 102, 241, 0.10)'
                      : 'transparent',
                } as const;
              }

              return (
                <tr key={row.id} style={{ background: dirty ? 'rgba(0,0,0,0.02)' : 'transparent' }}>
                  <td style={cellStyle(patch.outcome_name !== undefined)}>
                    <input
                      value={row.outcome_name || ''}
                      onChange={(e) => setField(row.id, 'outcome_name', e.target.value)}
                      style={{ width: 220 }}
                    />
                  </td>
                  <td style={cellStyle(patch.timepoint !== undefined)}>
                    <input
                      value={row.timepoint || ''}
                      onChange={(e) => setField(row.id, 'timepoint', e.target.value)}
                      style={{ width: 140 }}
                    />
                  </td>
                  <td style={cellStyle(patch.arm_intervention !== undefined)}>
                    <input
                      value={row.arm_intervention || ''}
                      onChange={(e) => setField(row.id, 'arm_intervention', e.target.value)}
                      style={{ width: 200 }}
                    />
                  </td>
                  <td style={cellStyle(patch.arm_control !== undefined)}>
                    <input
                      value={row.arm_control || ''}
                      onChange={(e) => setField(row.id, 'arm_control', e.target.value)}
                      style={{ width: 200 }}
                    />
                  </td>
                  <td style={cellStyle(patch.effect_measure !== undefined)}>
                    <select
                      value={row.effect_measure || 'OR'}
                      onChange={(e) => setField(row.id, 'effect_measure', e.target.value)}
                    >
                      <option value="OR">OR</option>
                      <option value="RR">RR</option>
                      <option value="HR">HR</option>
                    </select>
                  </td>

                  <td style={cellStyle(patch.a_events !== undefined, row.a_events != null && row.a_events < 0)}>
                    <input
                      value={row.a_events ?? ''}
                      onChange={(e) => setField(row.id, 'a_events', intOrNull(e.target.value))}
                      style={{ width: 70, borderColor: row.a_events === 0 ? 'var(--rc-danger)' : undefined }}
                      inputMode="numeric"
                    />
                  </td>
                  <td style={cellStyle(patch.b_non_events !== undefined, row.b_non_events != null && row.b_non_events < 0)}>
                    <input
                      value={row.b_non_events ?? ''}
                      onChange={(e) => setField(row.id, 'b_non_events', intOrNull(e.target.value))}
                      style={{ width: 70, borderColor: row.b_non_events === 0 ? 'var(--rc-danger)' : undefined }}
                      inputMode="numeric"
                    />
                  </td>
                  <td style={cellStyle(patch.c_events !== undefined, row.c_events != null && row.c_events < 0)}>
                    <input
                      value={row.c_events ?? ''}
                      onChange={(e) => setField(row.id, 'c_events', intOrNull(e.target.value))}
                      style={{ width: 70, borderColor: row.c_events === 0 ? 'var(--rc-danger)' : undefined }}
                      inputMode="numeric"
                    />
                  </td>
                  <td style={cellStyle(patch.d_non_events !== undefined, row.d_non_events != null && row.d_non_events < 0)}>
                    <input
                      value={row.d_non_events ?? ''}
                      onChange={(e) => setField(row.id, 'd_non_events', intOrNull(e.target.value))}
                      style={{ width: 70, borderColor: row.d_non_events === 0 ? 'var(--rc-danger)' : undefined }}
                      inputMode="numeric"
                    />
                  </td>

                  <td
                    style={{
                      ...cellStyle(false, invalidCounts),
                      background: mismatchOr ? 'rgba(250, 204, 21, 0.25)' : invalidCounts ? 'rgba(220,38,38,0.12)' : 'transparent',
                      color: mismatchOr ? '#92400e' : 'inherit',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {showOr != null ? showOr.toFixed(4) : '—'}
                    {mismatchOr ? <div style={{ fontSize: 11, opacity: 0.75 }}>recalc ≠ extracted</div> : null}
                    {!calc.ok ? (
                      <div style={{ fontSize: 11, opacity: 0.6, maxWidth: 160 }}>{calc.reason}{hasZeros ? ' (zeros)' : ''}</div>
                    ) : null}
                  </td>
                  <td style={{ ...cellStyle(false), whiteSpace: 'nowrap' }}>
                    {showCi ? `${showCi[0]!.toFixed(4)} – ${showCi[1]!.toFixed(4)}` : '—'}
                  </td>

                  <td style={cellStyle(patch.is_adjusted !== undefined)}>
                    <input
                      type="checkbox"
                      checked={Boolean(row.is_adjusted)}
                      onChange={(e) => setField(row.id, 'is_adjusted', e.target.checked)}
                    />
                  </td>

                  <td style={cellStyle(patch.adjusted_or !== undefined)}>
                    <input
                      value={row.adjusted_or ?? ''}
                      onChange={(e) => setField(row.id, 'adjusted_or', numOrNull(e.target.value))}
                      style={{ width: 110 }}
                      inputMode="decimal"
                    />
                  </td>
                  <td style={cellStyle(patch.adjusted_rr !== undefined)}>
                    <input
                      value={row.adjusted_rr ?? ''}
                      onChange={(e) => setField(row.id, 'adjusted_rr', numOrNull(e.target.value))}
                      style={{ width: 110 }}
                      inputMode="decimal"
                    />
                  </td>
                  <td style={cellStyle(patch.adjusted_hr !== undefined)}>
                    <input
                      value={row.adjusted_hr ?? ''}
                      onChange={(e) => setField(row.id, 'adjusted_hr', numOrNull(e.target.value))}
                      style={{ width: 110 }}
                      inputMode="decimal"
                    />
                  </td>
                  <td style={cellStyle(patch.adjustment_variables !== undefined)}>
                    <input
                      value={row.adjustment_variables || ''}
                      onChange={(e) => setField(row.id, 'adjustment_variables', e.target.value)}
                      style={{ width: 220 }}
                    />
                  </td>

                  <td style={cellStyle(patch.raw_extracted_value !== undefined)}>
                    <input
                      value={row.raw_extracted_value || ''}
                      onChange={(e) => setField(row.id, 'raw_extracted_value', e.target.value)}
                      style={{ width: 220 }}
                    />
                  </td>

                  <td style={cellStyle(patch.source_type !== undefined)}>
                    <select value={row.source_type || 'text'} onChange={(e) => setField(row.id, 'source_type', e.target.value)}>
                      <option value="text">text</option>
                      <option value="table">table</option>
                      <option value="figure">figure</option>
                      <option value="ocr">ocr</option>
                    </select>
                  </td>

                  <td style={cellStyle(patch.source_page !== undefined)}>
                    <input
                      value={row.source_page ?? ''}
                      onChange={(e) => setField(row.id, 'source_page', intOrNull(e.target.value))}
                      style={{ width: 90 }}
                      inputMode="numeric"
                    />
                  </td>

                  <td style={cellStyle(patch.confidence !== undefined)}>
                    <input
                      value={row.confidence ?? ''}
                      onChange={(e) => setField(row.id, 'confidence', numOrNull(e.target.value))}
                      style={{ width: 110 }}
                      inputMode="decimal"
                    />
                  </td>

                  <td style={cellStyle(patch.comments !== undefined)}>
                    <input
                      value={row.comments || ''}
                      onChange={(e) => setField(row.id, 'comments', e.target.value)}
                      style={{ width: 260 }}
                    />
                  </td>

                  <td style={{ ...cellStyle(false), whiteSpace: 'nowrap' }}>
                    <button onClick={() => clearDraft(row.id)} disabled={!dirty}>
                      Reset
                    </button>{' '}
                    <button onClick={() => deleteEffect(row.id)} style={{ background: 'rgba(220,38,38,0.10)' }}>
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { api } from '../../services/api';

type Artifact = { id: string; artifact_type: string };

type Props = {
  artifacts: Artifact[];
  summary: Record<string, unknown>;
};

function num(v: unknown): string {
  return typeof v === 'number' ? String(Math.round(v * 1000) / 1000) : '—';
}

// Renders the key pooled results plus an inline forest plot so the analyst can
// read the headline output without downloading anything.
export default function RunResultPreview({ artifacts, summary }: Props) {
  const forest = artifacts.find((a) => a.artifact_type.startsWith('figure_forest'));
  const forestId = forest?.id ?? null;
  const [svg, setSvg] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSvg(null);
    if (!forestId) return;
    setLoading(true);
    api
      .get(`/artifacts/${forestId}/download`, { responseType: 'text' })
      .then((r) => { if (!cancelled) setSvg(typeof r.data === 'string' ? r.data : null); })
      .catch(() => { if (!cancelled) setSvg(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [forestId]);

  const estimate = summary['estimate'];
  const ciLow = summary['ci_lower_95'];
  const ciHigh = summary['ci_upper_95'];
  const k = summary['k'];
  const i2 = summary['i_squared'];
  const p = summary['p_value'];
  const model = summary['model'];

  const hasStats = typeof estimate === 'number';

  if (!hasStats && !forest) return null;

  return (
    <div className="rc-card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {hasStats ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18 }}>
          <Stat label="Pooled estimate" value={`${num(estimate)} [${num(ciLow)}, ${num(ciHigh)}]`} strong />
          <Stat label="Studies (k)" value={num(k)} />
          <Stat label="I²" value={typeof i2 === 'number' ? `${num(i2)}%` : '—'} />
          <Stat label="p-value" value={num(p)} />
          <Stat label="Model" value={typeof model === 'string' ? model : '—'} />
        </div>
      ) : null}

      {loading ? <div className="rc-muted" style={{ fontSize: 13 }}>Rendering forest plot…</div> : null}
      {svg ? (
        <div
          style={{ width: '100%', overflowX: 'auto', border: '1px solid var(--rc-border)', borderRadius: 10, background: '#fff', padding: 8 }}
          // SVG is generated server-side from numeric inputs (no user HTML).
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : null}
    </div>
  );
}

function Stat({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--rc-muted)' }}>{label}</span>
      <span style={{ fontSize: strong ? 18 : 15, fontWeight: strong ? 800 : 600, color: 'var(--rc-text)' }}>{value}</span>
    </div>
  );
}

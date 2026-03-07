import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import MermaidBlock from './MermaidBlock';

type ProSection = {
  id: string;
  title: string;
  content_markdown: string;
};

type ProTable = {
  title: string;
  columns: string[];
  rows: any[][];
};

type ProChart = {
  title: string;
  type: 'bar' | 'line' | 'forest_like' | 'conceptual';
  data: any;
  note?: string | null;
};

type ProMermaid = {
  title: string;
  code: string;
};

type EvidenceMapRow = {
  question: string;
  conclusion: string;
  strength: 'high' | 'medium' | 'low';
  key_papers: string[];
  limitations?: string | null;
};

type ProOutput = {
  title: string;
  sections: ProSection[];
  tables?: ProTable[];
  charts?: ProChart[];
  mermaid?: ProMermaid[];
  evidence_map?: EvidenceMapRow[];
  references_vancouver?: string[];
  quality?: { evidence_strength: 'high' | 'medium' | 'low'; gaps?: string[] };
};

function strengthColor(s: string) {
  if (s === 'high') return 'rgba(34,197,94,0.20)';
  if (s === 'medium') return 'rgba(245,158,11,0.18)';
  return 'rgba(239,68,68,0.14)';
}

function MiniBarChart({ chart }: { chart: ProChart }) {
  // Best-effort: expect data: {labels:[], values:[]}
  const labels: string[] = Array.isArray(chart.data?.labels) ? chart.data.labels : [];
  const values: number[] = Array.isArray(chart.data?.values) ? chart.data.values.map((x: any) => Number(x) || 0) : [];
  const max = Math.max(1, ...values);

  if (!labels.length || labels.length !== values.length) {
    return (
      <div style={{ fontSize: 12, opacity: 0.85 }}>
        <div style={{ opacity: 0.8 }}>No quantitative chart data provided.</div>
        <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, opacity: 0.85 }}>{JSON.stringify(chart.data || {}, null, 2)}</pre>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {labels.map((l, i) => (
        <div key={l + i} style={{ display: 'grid', gridTemplateColumns: '160px 1fr 60px', gap: 8, alignItems: 'center' }}>
          <div style={{ fontSize: 12, opacity: 0.85 }}>{l}</div>
          <div style={{ height: 10, background: 'rgba(0,0,0,0.08)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: `${Math.max(0, Math.min(100, (values[i] / max) * 100))}%`, height: '100%', background: 'rgba(59,130,246,0.5)' }} />
          </div>
          <div style={{ fontSize: 12, opacity: 0.75, textAlign: 'right' }}>{values[i].toFixed(2)}</div>
        </div>
      ))}
    </div>
  );
}

export default function ClinicalProViewer({ pro }: { pro: ProOutput }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <div style={{ fontWeight: 900, fontSize: 18 }}>{pro.title}</div>
        {pro.quality ? (
          <div style={{ fontSize: 12, opacity: 0.85, marginTop: 6 }}>
            <span style={{ padding: '2px 8px', borderRadius: 999, background: strengthColor(pro.quality.evidence_strength), border: '1px solid rgba(0,0,0,0.10)' }}>
              Evidence: {pro.quality.evidence_strength}
            </span>
            {pro.quality.gaps?.length ? <span style={{ marginLeft: 10, opacity: 0.75 }}>gaps: {pro.quality.gaps.join(', ')}</span> : null}
          </div>
        ) : null}
      </div>

      {pro.sections?.map((s) => (
        <div key={s.id}>
          <h2 id={s.id} style={{ marginTop: 18 }}>
            {s.title}
          </h2>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{s.content_markdown || ''}</ReactMarkdown>
        </div>
      ))}

      {pro.tables?.length ? (
        <div>
          <h2>Tablas</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {pro.tables.map((t, idx) => (
              <div key={t.title + idx} style={{ border: '1px solid rgba(0,0,0,0.10)', borderRadius: 10, padding: 10 }}>
                <div style={{ fontWeight: 800, marginBottom: 8 }}>{t.title}</div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead>
                      <tr>
                        {t.columns.map((c) => (
                          <th key={c} style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, background: 'rgba(0,0,0,0.04)', textAlign: 'left' }}>
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {t.rows.map((row, ri) => (
                        <tr key={ri}>
                          {row.map((cell, ci) => (
                            <td key={ci} style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>
                              {String(cell ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {pro.charts?.length ? (
        <div>
          <h2>Gráficos</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {pro.charts.map((ch, idx) => (
              <div key={ch.title + idx} style={{ border: '1px solid rgba(0,0,0,0.10)', borderRadius: 10, padding: 10 }}>
                <div style={{ fontWeight: 800 }}>{ch.title}</div>
                <div style={{ fontSize: 12, opacity: 0.75 }}>type: {ch.type}</div>
                {ch.note ? <div style={{ fontSize: 12, opacity: 0.8, marginTop: 6 }}>{ch.note}</div> : null}
                <div style={{ marginTop: 10 }}>
                  {ch.type === 'bar' ? <MiniBarChart chart={ch} /> : <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, opacity: 0.85 }}>{JSON.stringify(ch.data || {}, null, 2)}</pre>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {pro.mermaid?.length ? (
        <div>
          <h2>Diagramas</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {pro.mermaid.map((m, idx) => (
              <div key={m.title + idx} style={{ border: '1px solid rgba(0,0,0,0.10)', borderRadius: 10, padding: 10 }}>
                <div style={{ fontWeight: 800, marginBottom: 8 }}>{m.title}</div>
                <MermaidBlock code={m.code} />
                <details style={{ marginTop: 8 }}>
                  <summary style={{ fontSize: 12, opacity: 0.8, cursor: 'pointer' }}>Show mermaid code</summary>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, opacity: 0.85 }}>{m.code}</pre>
                </details>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {pro.evidence_map?.length ? (
        <div>
          <h2>Mapa de evidencia</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  {['Pregunta', 'Conclusión', 'Fuerza', 'Papers clave', 'Limitaciones'].map((c) => (
                    <th key={c} style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, background: 'rgba(0,0,0,0.04)', textAlign: 'left' }}>
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pro.evidence_map.map((r, idx) => (
                  <tr key={idx}>
                    <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>{r.question}</td>
                    <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>{r.conclusion}</td>
                    <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>{r.strength}</td>
                    <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>{(r.key_papers || []).join(', ')}</td>
                    <td style={{ border: '1px solid rgba(0,0,0,0.12)', padding: 6, verticalAlign: 'top' }}>{r.limitations || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {pro.references_vancouver?.length ? (
        <div>
          <h2>Referencias</h2>
          <ol>
            {pro.references_vancouver.map((x, i) => (
              <li key={i} style={{ fontSize: 13, opacity: 0.95 }}>
                {x}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

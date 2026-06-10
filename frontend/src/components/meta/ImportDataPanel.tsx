import { useState } from 'react';
import { api } from '../../services/api';
import { useToast } from '../../ui/Toast/ToastProvider';

type Props = {
  projectId: string;
  onImported?: () => void;
};

// Columns accepted in the pasted CSV. study_label groups rows into studies;
// every other column maps onto an effect size. Binary outcomes can be given
// either as 2x2 counts (a_events..d_non_events) or as a precomputed
// effect_value + effect_se / ci.
const NUMERIC_COLUMNS = new Set([
  'a_events', 'b_non_events', 'c_events', 'd_non_events', 'events_total', 'total_n',
  'or_value', 'log_or', 'se_log_or', 'effect_value', 'effect_se', 'ci_lower_95', 'ci_upper_95',
  'n_intervention', 'n_control', 'mean_intervention', 'sd_intervention', 'mean_control', 'sd_control',
  'year',
]);

const EXAMPLE = `study_label,year,outcome_name,effect_measure,outcome_type,arm_intervention,arm_control,a_events,b_non_events,c_events,d_non_events
Granger 2011 (ARISTOTLE),2011,Stroke/SE,OR,binary,Apixaban,Warfarin,212,8908,265,8795
Patel 2011 (ROCKET-AF),2011,Stroke/SE,OR,binary,Rivaroxaban,Warfarin,269,6989,306,6985
Connolly 2009 (RE-LY),2009,Stroke/SE,OR,binary,Dabigatran,Warfarin,134,5973,199,5823
Giugliano 2013 (ENGAGE),2013,Stroke/SE,OR,binary,Edoxaban,Warfarin,296,6739,337,6695`;

function splitCsvLine(line: string): string[] {
  const out: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { cur += '"'; i++; } else { inQuotes = !inQuotes; }
    } else if (ch === ',' && !inQuotes) {
      out.push(cur); cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

const STUDY_FIELDS = new Set(['study_label', 'authors', 'year', 'design', 'country', 'population', 'doi', 'pmid', 'notes']);

type ParsedStudy = {
  study_label: string;
  authors?: string;
  year?: number;
  design?: string;
  doi?: string;
  pmid?: string;
  effects: Record<string, unknown>[];
};

function parseCsv(text: string): { studies: ParsedStudy[]; error: string | null } {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length < 2) return { studies: [], error: 'Pega al menos una fila de encabezado y una de datos.' };
  const headers = splitCsvLine(lines[0]).map((h) => h.toLowerCase());
  if (!headers.includes('study_label')) return { studies: [], error: 'Falta la columna obligatoria "study_label".' };
  if (!headers.includes('outcome_name')) return { studies: [], error: 'Falta la columna obligatoria "outcome_name".' };

  const byLabel = new Map<string, ParsedStudy>();
  for (let r = 1; r < lines.length; r++) {
    const cells = splitCsvLine(lines[r]);
    const row: Record<string, string> = {};
    headers.forEach((h, i) => { row[h] = cells[i] ?? ''; });
    const label = row['study_label'];
    if (!label) continue;

    if (!byLabel.has(label)) {
      byLabel.set(label, {
        study_label: label,
        authors: row['authors'] || undefined,
        year: row['year'] ? Number(row['year']) : undefined,
        design: row['design'] || undefined,
        doi: row['doi'] || undefined,
        pmid: row['pmid'] || undefined,
        effects: [],
      });
    }
    const effect: Record<string, unknown> = {};
    for (const h of headers) {
      if (STUDY_FIELDS.has(h)) continue;
      const raw = row[h];
      if (raw === '' || raw === undefined) continue;
      effect[h] = NUMERIC_COLUMNS.has(h) ? Number(raw) : raw;
    }
    if (!effect['arm_intervention']) effect['arm_intervention'] = 'Intervention';
    if (!effect['arm_control']) effect['arm_control'] = 'Control';
    byLabel.get(label)!.effects.push(effect);
  }
  return { studies: Array.from(byLabel.values()), error: null };
}

export default function ImportDataPanel({ projectId, onImported }: Props) {
  const toast = useToast();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<ParsedStudy[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function doPreview() {
    setError(null);
    const { studies, error: err } = parseCsv(text);
    if (err) { setError(err); setPreview(null); return; }
    setPreview(studies);
  }

  async function doImport() {
    const { studies, error: err } = parseCsv(text);
    if (err) { setError(err); return; }
    setBusy(true);
    setError(null);
    try {
      const r = await api.post('/meta/studies/import', { project_id: projectId, studies });
      toast.success('Datos importados', `${r.data?.imported_studies ?? studies.length} estudios listos para la matriz.`);
      setText('');
      setPreview(null);
      onImported?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'No se pudo importar.');
    } finally {
      setBusy(false);
    }
  }

  const totalEffects = preview?.reduce((n, s) => n + s.effects.length, 0) ?? 0;

  return (
    <div className="rc-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <div className="rc-card-title" style={{ marginBottom: 4 }}>Importar datos extraídos (CSV)</div>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--rc-muted)' }}>
          ¿Ya tienes tus datos? Pega un CSV y corre el meta-análisis sin LLM ni PDFs. Para desenlaces binarios
          basta con las tablas 2×2 (<code>a_events…d_non_events</code>); el log-OR/RR y su EE se calculan automáticamente.
        </p>
      </div>

      <textarea
        className="rc-textarea"
        style={{ minHeight: 150, fontFamily: 'ui-monospace, monospace', fontSize: 12 }}
        placeholder="study_label,outcome_name,effect_measure,arm_intervention,arm_control,a_events,b_non_events,c_events,d_non_events"
        value={text}
        onChange={(e) => { setText(e.target.value); setPreview(null); }}
      />

      <div className="rc-row" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="rc-btn rc-btn--sm" type="button" onClick={() => { setText(EXAMPLE); setPreview(null); setError(null); }}>
          Cargar ejemplo (DOAC vs warfarina)
        </button>
        <button className="rc-btn rc-btn--sm" type="button" onClick={doPreview} disabled={!text.trim()}>
          Previsualizar
        </button>
        <button className="rc-btn rc-btn--sm rc-btn--primary" type="button" onClick={doImport} disabled={busy || !text.trim()}>
          {busy ? 'Importando…' : 'Importar al proyecto'}
        </button>
      </div>

      {error ? <div className="rc-error" style={{ fontSize: 13 }}>{error}</div> : null}

      {preview ? (
        <div style={{ fontSize: 13, color: 'var(--rc-text-secondary)' }}>
          <strong>{preview.length}</strong> estudios · <strong>{totalEffects}</strong> efectos detectados:
          <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
            {preview.slice(0, 6).map((s) => (
              <li key={s.study_label}>{s.study_label} — {s.effects.length} efecto(s)</li>
            ))}
            {preview.length > 6 ? <li>… y {preview.length - 6} más</li> : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

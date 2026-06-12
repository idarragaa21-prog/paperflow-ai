const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const fmt = (x, dp = 2) => (x === null || x === undefined || Number.isNaN(x)) ? '—' : Number(x).toFixed(dp);

const MEASURE_LABEL = {
  OR: 'Odds ratio', RR: 'Riesgo relativo', RD: 'Diferencia de riesgos', HR: 'Hazard ratio',
  IRR: 'Tasa de incidencia', MD: 'Diferencia de medias', SMD: 'Dif. media estandarizada',
  PLOGIT: 'Proporción', ZCOR: 'Correlación', GEN: 'Genérico / cualitativo',
};
const MEASURE_KIND = { OR: '2x2', RR: '2x2', RD: '2x2', HR: 'precomputed', IRR: 'person_time', MD: 'continuous', SMD: 'continuous', PLOGIT: 'proportion', ZCOR: 'correlation', GEN: 'generic' };
const KIND_COLS = {
  '2x2': 'study_label, effect_measure, a_events, b_non_events, c_events, d_non_events',
  person_time: 'study_label, effect_measure, events_intervention, time_intervention, events_control, time_control',
  continuous: 'study_label, effect_measure, n_intervention, mean_intervention, sd_intervention, n_control, mean_control, sd_control',
  proportion: 'study_label, effect_measure, events, n_total',
  correlation: 'study_label, effect_measure, r, n_total',
  precomputed: 'study_label, effect_measure, effect_value, ci_lower_95, ci_upper_95',
  generic: 'study_label, effect_measure, yi, se',
};
const SECTION_TITLES = { title: 'Título', abstract: 'Resumen', introduction: 'Introducción', methods: 'Métodos', results: 'Resultados', discussion: 'Discusión', limitations: 'Limitaciones', conclusion: 'Conclusión' };
const SECTION_ORDER = ['title', 'abstract', 'introduction', 'methods', 'results', 'discussion', 'limitations', 'conclusion'];

const S = { step: 1, ai: false, questionText: '', measure: 'OR', chosen: null, protocol: null,
  result: null, manuscript: {}, flow: 'intervención', fhigh: 'control', examples: {} };

function downloadText(name, text, type) {
  const blob = new Blob([text], { type: type || 'text/plain' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  URL.revokeObjectURL(a.href);
}
async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); if (btn) { const t = btn.textContent; btn.textContent = '✓'; setTimeout(() => btn.textContent = t, 1200); } } catch {}
}

// ---------- Step navigation ----------
const setStepEnabled = (n, on) => { const b = $('navstep-' + n); if (b) b.disabled = !on; };
const markDone = (n) => $('navstep-' + n) && $('navstep-' + n).classList.add('done');
function goStep(n) {
  S.step = n;
  document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + n));
  document.querySelectorAll('.step').forEach((b) => b.classList.toggle('active', b.dataset.step === String(n)));
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (n === 6 && S.result && !Object.keys(S.manuscript).length) $('draftBtn').click();
}
$('steps').addEventListener('click', (e) => { const b = e.target.closest('.step'); if (b && !b.disabled) goStep(Number(b.dataset.step)); });

// ---------- Init ----------
async function init() {
  try { S.ai = !!(await (await fetch('/ai-status')).json()).ai_available; } catch { S.ai = false; }
  const pill = $('aiPill');
  pill.classList.add(S.ai ? 'on' : 'off');
  pill.textContent = S.ai ? '● IA activa' : '○ Modo local';
  pill.title = S.ai ? 'Usando tu sesión de Claude' : 'Inicia sesión con: claude login';
  $('forgeHint').textContent = S.ai
    ? 'Usando tu sesión de Claude (tus tokens). Tarda unos segundos.'
    : 'Modo local (plantillas). Para IA, ejecuta «claude login» en tu equipo.';
  try {
    S.examples = await (await fetch('/examples')).json();
    const sel = $('exampleSel');
    Object.entries(S.examples).forEach(([k, v]) => { const o = document.createElement('option'); o.value = k; o.textContent = v.title; sel.appendChild(o); });
  } catch {}
}

function busy(btn, on, label) {
  if (on) {
    if (!btn._timer) btn.dataset.label = btn.innerHTML;
    btn.disabled = true;
    const base = label || 'Trabajando…';
    const t0 = Date.now();
    const paint = () => { const s = Math.round((Date.now() - t0) / 1000); btn.innerHTML = `<span class="spinner"></span> ${base}${s > 2 ? ` (${s}s)` : ''}`; };
    paint();
    if (btn._timer) clearInterval(btn._timer);
    btn._timer = setInterval(paint, 1000);
  } else {
    if (btn._timer) { clearInterval(btn._timer); btn._timer = null; }
    btn.disabled = false; btn.innerHTML = btn.dataset.label || label || '';
  }
}

// ---------- STEP 1: questions ----------
$('genBtn').onclick = async () => {
  const topic = $('topic').value.trim();
  $('genErr').textContent = '';
  if (!topic) { $('genErr').textContent = 'Escribe un tema primero.'; return; }
  const btn = $('genBtn'); busy(btn, true, 'Forjando preguntas…');
  try {
    const r = await fetch('/questions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, n: Number($('nq').value), mode: 'auto' }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'No se pudieron generar preguntas');
    S.questions = data.questions;
    renderQuestions(data);
  } catch (e) { $('genErr').textContent = e.message; } finally { busy(btn, false); }
};
$('topic').onkeydown = (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('genBtn').click(); };

const picoRow = (label, val) => val ? `<div><b>${label}</b>${esc(val)}</div>` : '';
function renderQuestions(data) {
  const srcNote = data.source === 'ai'
    ? '<p class="muted" style="margin:0 0 4px">Generadas con IA a partir de tu tema.</p>'
    : `<p class="note">Modo local: plantillas. ${data.ai_error ? 'La IA no respondió. ' : ''}Para preguntas completas en cualquier idioma, inicia sesión con <code>claude login</code>.</p>`;
  const cards = data.questions.map((q, i) => {
    const ml = MEASURE_LABEL[q.measure] || q.measure;
    const pico = [picoRow('Población', q.population), picoRow('Exposición/Interv.', q.exposure), picoRow('Comparador', q.comparator), picoRow('Desenlace', q.outcome)].join('');
    return `<div class="qcard">
      <div class="qtext">${esc(q.question)}</div>
      <div class="qbadges"><span class="badge primary">${esc(q.framework)}</span><span class="badge measure">${esc(ml)}</span>${q.design ? `<span class="badge">${esc(q.design.slice(0, 64))}</span>` : ''}</div>
      ${pico ? `<div class="pico">${pico}</div>` : ''}
      ${q.finer ? `<p class="muted" style="margin:0 0 10px">⚖ ${esc(q.finer)}</p>` : ''}
      <div class="qfoot"><span class="rationale">${esc(q.rationale || '')}</span><button class="btn btn-primary btn-sm" data-use="${i}">Usar esta pregunta →</button></div>
    </div>`;
  }).join('');
  $('questions').innerHTML = srcNote + cards;
  $('questions').querySelectorAll('[data-use]').forEach((b) => { b.onclick = () => useQuestion(S.questions[Number(b.dataset.use)]); });
}

function useQuestion(q) {
  S.chosen = q; S.questionText = q.question; S.measure = q.measure || 'OR'; S.protocol = null;
  setStepEnabled(2, true); setStepEnabled(3, true); markDone(1);
  prepareProtocolStep(); prepareDataStep();
  goStep(2);
}
$('skipToData').onclick = () => {
  S.chosen = null; S.questionText = ''; S.measure = 'OR';
  setStepEnabled(3, true); markDone(1); prepareDataStep(); goStep(3);
};

// ---------- STEP 2: protocol ----------
function prepareProtocolStep() {
  if (S.chosen) {
    $('protoChosen').style.display = '';
    $('protoChosen').innerHTML = `<b>Pregunta:</b> ${esc(S.chosen.question)}`;
  } else { $('protoChosen').style.display = 'none'; }
  $('protoBody').innerHTML = '';
}
$('protoBtn').onclick = async () => {
  $('protoErr').textContent = '';
  if (!S.questionText) { $('protoErr').textContent = 'Elige una pregunta primero.'; return; }
  const btn = $('protoBtn'); busy(btn, true, 'Generando…');
  try {
    const r = await fetch('/protocol', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: S.questionText, measure: S.measure, mode: 'auto' }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'No se pudo generar el protocolo');
    S.protocol = data.protocol;
    renderProtocol(data);
  } catch (e) { $('protoErr').textContent = e.message; } finally { busy(btn, false); }
};
function listBlock(title, items) {
  if (!items || !items.length) return '';
  return `<div class="proto-block"><h4>${title}</h4><ul class="proto-list">${items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul></div>`;
}
function chipsBlock(title, items) {
  if (!items || !items.length) return '';
  return `<div class="proto-block"><h4>${title}</h4><div class="chips">${items.map((x) => `<span class="chip">${esc(x)}</span>`).join('')}</div></div>`;
}
function renderProtocol(data) {
  const p = data.protocol;
  const note = data.source === 'local' ? '<p class="note">Modo local: plantilla base. Con <code>claude login</code> obtienes criterios y búsqueda a medida.</p>' : '';
  $('protoBody').innerHTML = note +
    (p.objective ? `<div class="proto-block"><h4>Objetivo</h4><p style="font-size:13.5px;margin:0">${esc(p.objective)}</p></div>` : '') +
    listBlock('Criterios de inclusión', p.inclusion_criteria) +
    listBlock('Criterios de exclusión', p.exclusion_criteria) +
    chipsBlock('Diseños elegibles', p.study_designs) +
    listBlock('Desenlaces', p.outcomes) +
    (p.search_pubmed ? `<div class="proto-block"><h4>Búsqueda en PubMed</h4><div class="codebox">${esc(p.search_pubmed)}<button class="btn btn-sm copy" data-copy="pubmed">Copiar</button></div></div>` : '') +
    chipsBlock('Palabras clave', p.keywords) +
    chipsBlock('Campos a extraer (columnas del CSV)', p.extraction_fields) +
    (p.prisma_note ? `<p class="muted" style="margin-top:12px">📋 ${esc(p.prisma_note)}</p>` : '');
  const cp = $('protoBody').querySelector('[data-copy="pubmed"]');
  if (cp) cp.onclick = () => copy(p.search_pubmed, cp);
  $('protoDl').style.display = '';
}
function protocolMarkdown(p) {
  const L = (t, arr) => (arr && arr.length) ? `## ${t}\n` + arr.map((x) => `- ${x}`).join('\n') + '\n\n' : '';
  return `# Protocolo de revisión\n\n` +
    (S.questionText ? `**Pregunta:** ${S.questionText}\n\n` : '') +
    (p.objective ? `**Objetivo:** ${p.objective}\n\n` : '') +
    L('Criterios de inclusión', p.inclusion_criteria) +
    L('Criterios de exclusión', p.exclusion_criteria) +
    L('Diseños elegibles', p.study_designs) +
    L('Desenlaces', p.outcomes) +
    (p.search_pubmed ? `## Búsqueda en PubMed\n\n\`\`\`\n${p.search_pubmed}\n\`\`\`\n\n` : '') +
    L('Palabras clave', p.keywords) +
    L('Campos a extraer (columnas del CSV)', p.extraction_fields) +
    (p.prisma_note ? `## PRISMA\n${p.prisma_note}\n` : '');
}
$('protoDl').onclick = () => S.protocol && downloadText('protocolo_metaforge.md', protocolMarkdown(S.protocol), 'text/markdown');
$('toData').onclick = () => goStep(3);

// ---------- STEP 3: data ----------
function prepareDataStep() {
  const ml = MEASURE_LABEL[S.measure] || S.measure;
  const kind = MEASURE_KIND[S.measure] || '2x2';
  if (S.chosen) { $('chosenBanner').style.display = ''; $('chosenBanner').innerHTML = `<b>Pregunta:</b> ${esc(S.chosen.question)}<br><b>Medida sugerida:</b> ${esc(ml)}`; }
  else { $('chosenBanner').style.display = 'none'; }
  $('measureHint').innerHTML = S.measure === 'GEN'
    ? 'Pregunta cualitativa/descriptiva: el meta-análisis cuantitativo puede no aplicar. Si tienes efectos numéricos, usa columnas <code>yi, se</code>.'
    : `Para <b>${esc(ml)}</b> usa columnas: <code>${esc(KIND_COLS[kind])}</code>`;
  const match = Object.entries(S.examples).find(([, v]) => (v.title || '').toUpperCase().includes(`(${S.measure}`));
  if (match) $('exampleSel').value = match[0];
}
$('exampleSel').onchange = async (e) => {
  const key = e.target.value; if (!key) return;
  const data = await (await fetch('/examples/' + key)).json();
  $('csv').value = data.csv.trim();
  if (data.favours_low) S.flow = data.favours_low;
  if (data.favours_high) S.fhigh = data.favours_high;
};
$('clearData').onclick = () => { $('csv').value = ''; };
$('tplBtn').onclick = () => { window.location = '/templates/' + (MEASURE_KIND[S.measure] || '2x2'); };
$('formatHelp').onclick = () => {
  const box = $('formatBox'); const kind = MEASURE_KIND[S.measure] || '2x2';
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
  box.innerHTML = `<b>Una fila por estudio.</b> Requeridas: <code>study_label</code>, <code>effect_measure</code>. Opcionales: <code>year</code> (acumulativo), <code>subgroup</code> (subgrupos).<br>Para tu medida (${esc(MEASURE_LABEL[S.measure] || S.measure)}): <code>${esc(KIND_COLS[kind])}</code>`;
};
$('analyzeBtn').onclick = () => runAnalysis(true);
$('rerunBtn').onclick = () => runAnalysis(false);

async function runAnalysis(advance) {
  $('dataErr').textContent = '';
  $('flow').value = $('flow').value || S.flow; $('fhigh').value = $('fhigh').value || S.fhigh;
  const body = { csv: $('csv').value, model: $('model').value, tau2_method: $('tau2').value, knapp_hartung: $('kh').checked, favours_low: $('flow').value || S.flow, favours_high: $('fhigh').value || S.fhigh };
  const btn = advance ? $('analyzeBtn') : $('rerunBtn'); busy(btn, true, 'Analizando…');
  try {
    const r = await fetch('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error en el análisis');
    S.result = data;
    S.measure = data.measure || S.measure;
    renderSynthesis(data); renderDiagnostics(data);
    setStepEnabled(4, true); setStepEnabled(5, true); setStepEnabled(6, true);
    markDone(3); $('noResult').style.display = 'none'; $('articleWrap').style.display = '';
    if (advance) goStep(4);
  } catch (e) { $('dataErr').textContent = e.message; } finally { busy(btn, false); }
}

// ---------- STEP 4: synthesis ----------
const stat = (k, v, big) => `<div class="stat ${big ? 'big' : ''}"><div class="k">${k}</div><div class="v">${v}</div></div>`;
function interpret(d) {
  const p = d.pooled, ratio = d.log_scale;
  const sig = ratio ? (p.ci_low > 1 || p.ci_high < 1) : (p.ci_low > 0 || p.ci_high < 0);
  const dir = ratio ? (p.estimate < 1 ? 'una reducción' : 'un aumento') : (p.estimate < 0 ? 'un efecto hacia la izquierda' : 'un efecto hacia la derecha');
  const het = d.heterogeneity.i2 >= 75 ? 'considerable' : d.heterogeneity.i2 >= 50 ? 'sustancial' : d.heterogeneity.i2 >= 30 ? 'moderada' : 'baja';
  let s = `El ${(d.measure_label || d.measure).toLowerCase()} combinado es <b>${fmt(p.estimate)}</b> (IC 95% ${fmt(p.ci_low)}–${fmt(p.ci_high)}, p=${fmt(p.p_value, 3)}), `;
  s += sig ? `indicando ${dir} estadísticamente significativa. ` : `sin diferencia estadísticamente significativa. `;
  s += `La heterogeneidad entre estudios es <b>${het}</b> (I²=${fmt(d.heterogeneity.i2, 0)}%).`;
  if (p.pi_low != null) s += ` El intervalo de predicción 95% (${fmt(p.pi_low)}–${fmt(p.pi_high)}) es el rango esperado para un estudio futuro.`;
  return s;
}
function renderSynthesis(d) {
  const p = d.pooled, h = d.heterogeneity, m = d.measure;
  $('stats').innerHTML = [stat(`${m} combinado`, `${fmt(p.estimate)} [${fmt(p.ci_low)}, ${fmt(p.ci_high)}]`, true), stat('Estudios', d.k), stat('p-valor', fmt(p.p_value, 4)), stat('I²', fmt(h.i2, 0) + '%'), stat('τ²', fmt(h.tau2, 3)), p.pi_low != null ? stat('Predicción 95%', `[${fmt(p.pi_low)}, ${fmt(p.pi_high)}]`) : ''].join('');
  $('interp').innerHTML = interpret(d);
  const model = d.model === 'random' ? `efectos aleatorios (${d.tau2_method}${d.knapp_hartung ? ', Knapp-Hartung' : ''})` : 'efecto fijo';
  $('hetero').innerHTML = `Modelo: ${model}. Q=${fmt(h.q)} (gl=${h.q_df}, p=${fmt(h.q_p, 3)}), I²=${fmt(h.i2, 0)}%, τ²=${fmt(h.tau2, 4)}, H²=${fmt(h.h2)}.`;
  $('warnings').innerHTML = (d.warnings && d.warnings.length) ? `<div class="note"><b>Avisos:</b> ${d.warnings.map(esc).join(' · ')}</div>` : '';
  $('forest').innerHTML = d.forest_svg;
}
$('toDiag').onclick = () => goStep(5);
$('toArticle').onclick = () => goStep(6);

// ---------- STEP 5: diagnostics ----------
function renderDiagnostics(d) {
  const m = d.measure;
  $('loo').innerHTML = d.loo_forest_svg || '<div class="empty">Se necesitan ≥3 estudios.</div>';
  if (d.cumulative && d.cumulative.length) {
    const hasYears = $('csv').value.toLowerCase().includes('year');
    $('cumNote').textContent = hasYears ? 'En orden cronológico (columna year).' : 'Orden de entrada (añade year para orden cronológico).';
    $('cumTable').innerHTML = `<tr><th>+ Estudio</th><th>k</th><th>${m} acum. [IC95%]</th><th>I²</th><th>p</th></tr>` + d.cumulative.map((c) => `<tr><td>${esc(c.added)}</td><td>${c.k}</td><td>${fmt(c.estimate)} [${fmt(c.ci_low)}, ${fmt(c.ci_high)}]</td><td>${fmt(c.i2, 0)}%</td><td>${fmt(c.p_value, 3)}</td></tr>`).join('');
  } else { $('cumTable').innerHTML = ''; $('cumNote').textContent = ''; }
  if (d.subgroups) {
    const s = d.subgroups;
    const rows = s.groups.map((g) => `<tr><td>${esc(g.subgroup)}</td><td>${g.k}</td><td>${fmt(g.estimate)} [${fmt(g.ci_low)}, ${fmt(g.ci_high)}]</td><td>${fmt(g.i2, 0)}%</td></tr>`).join('');
    const sigTxt = s.p_value < 0.05 ? `<b>Hay diferencia significativa</b> entre subgrupos (p=${fmt(s.p_value, 3)}).` : `Sin evidencia de diferencia entre subgrupos (p=${fmt(s.p_value, 3)}).`;
    $('subCard').innerHTML = `<div class="card-head"><h3>Subgrupos</h3></div><div class="tbl-wrap"><table><tr><th>Subgrupo</th><th>k</th><th>${m} [IC95%]</th><th>I²</th></tr>${rows}</table></div><div class="interp" style="margin-top:12px">Prueba entre subgrupos: Q=${fmt(s.q_between)} (gl=${s.df}). ${sigTxt}</div>`;
  } else { $('subCard').innerHTML = `<div class="card-head"><h3>Subgrupos</h3></div><div class="empty">Añade una columna <code>subgroup</code> (≥2 valores) para comparar subgrupos.</div>`; }
  $('funnel').innerHTML = d.funnel_svg;
  $('baujat').innerHTML = d.baujat_svg || '<div class="empty">≥3 estudios para Baujat.</div>';
  if (d.egger) { $('egger').innerHTML = `<b>Prueba de Egger:</b> intercepto=${fmt(d.egger.intercept)}, p=${fmt(d.egger.p_value, 3)}. ${d.egger.p_value < 0.05 ? '<span style="color:var(--warn)">Asimetría significativa: posible sesgo.</span>' : 'Sin evidencia fuerte de asimetría.'} ${d.egger.note ? '<span class="muted">— ' + esc(d.egger.note) + '</span>' : ''}`; }
  else { $('egger').innerHTML = '<span class="muted">Prueba de Egger: ≥3 estudios.</span>'; }
  if (d.trim_fill) { const t = d.trim_fill; $('trimfill').innerHTML = t.k0 > 0 ? `<b>Trim-and-fill:</b> se estiman <b>${t.k0}</b> estudio(s) faltante(s) al lado <b>${t.side === 'left' ? 'izquierdo' : 'derecho'}</b>. Observado ${fmt(t.observed_estimate)} → ajustado <b>${fmt(t.adjusted_estimate)}</b> [${fmt(t.adjusted_ci_low)}, ${fmt(t.adjusted_ci_high)}]. (círculos rojos en el funnel)` : `<b>Trim-and-fill:</b> no se estiman estudios faltantes (k0=0); funnel simétrico según este método.`; }
  else { $('trimfill').innerHTML = '<span class="muted">Trim-and-fill: ≥3 estudios.</span>'; }
  const rows = d.studies.map((s) => `<tr><td>${esc(s.label)}</td>${d.subgroups ? `<td>${esc(s.subgroup || '—')}</td>` : ''}<td>${fmt(s.estimate)}</td><td>[${fmt(s.ci_low)}, ${fmt(s.ci_high)}]</td><td>${fmt(s.weight_pct, 1)}%</td><td class="muted">${esc(s.note || '')}</td></tr>`).join('');
  $('studies').innerHTML = `<tr><th>Estudio</th>${d.subgroups ? '<th>Subgrupo</th>' : ''}<th>${m}</th><th>IC 95%</th><th>Peso</th><th>Nota</th></tr>${rows}`;
}

// ---------- STEP 6: article ----------
function autoGrow(ta) { ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight + 2, 1200) + 'px'; }
function questionForArticle() { return S.questionText || ('Meta-análisis de ' + (MEASURE_LABEL[S.measure] || S.measure)); }
$('draftBtn').onclick = async () => {
  if (!S.result) return;
  const btn = $('draftBtn'); busy(btn, true, 'Redactando…');
  try {
    const r = await fetch('/manuscript', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: questionForArticle(), result: S.result, protocol: S.protocol, mode: 'local' }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    S.manuscript = data.sections;
    $('facts').textContent = data.facts || '';
    renderSections();
    if (S.ai) $('aiAllBtn').style.display = '';
  } catch (e) { alert(e.message); } finally { busy(btn, false); }
};
$('aiAllBtn').onclick = async () => {
  const btn = $('aiAllBtn'); const orig = btn.dataset.label || btn.innerHTML; btn.dataset.label = orig; btn.disabled = true;
  for (let i = 0; i < SECTION_ORDER.length; i++) {
    const sec = SECTION_ORDER[i];
    btn.innerHTML = `<span class="spinner"></span> Redactando ${i + 1}/${SECTION_ORDER.length}…`;
    const cardBtn = $('sections').querySelector(`[data-ai="${sec}"]`);
    await improveSection(sec, cardBtn || document.createElement('button'), true);
  }
  btn.disabled = false; btn.innerHTML = orig;
};
function renderSections() {
  $('sections').innerHTML = SECTION_ORDER.map((sec) => `
    <div class="sec" data-sec="${sec}">
      <div class="sec-head"><h4>${SECTION_TITLES[sec]}</h4>
        <div class="sec-actions">
          ${S.ai ? `<button class="btn btn-mini" data-ai="${sec}">✦ Mejorar con IA</button>` : ''}
          <button class="btn btn-mini" data-copy="${sec}">Copiar</button>
        </div>
      </div>
      <textarea data-ta="${sec}">${esc(S.manuscript[sec] || '')}</textarea>
    </div>`).join('');
  $('sections').querySelectorAll('textarea').forEach((ta) => { autoGrow(ta); ta.oninput = () => { S.manuscript[ta.dataset.ta] = ta.value; autoGrow(ta); }; });
  $('sections').querySelectorAll('[data-copy]').forEach((b) => { b.onclick = () => copy(S.manuscript[b.dataset.copy] || '', b); });
  $('sections').querySelectorAll('[data-ai]').forEach((b) => { b.onclick = () => improveSection(b.dataset.ai, b); });
}
async function improveSection(sec, btn, silent) {
  busy(btn, true, 'IA…');
  try {
    const r = await fetch('/manuscript/section', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: questionForArticle(), result: S.result, section: sec, protocol: S.protocol, mode: 'ai' }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    S.manuscript[sec] = data.text;
    const ta = $('sections').querySelector(`[data-ta="${sec}"]`); if (ta) { ta.value = data.text; autoGrow(ta); }
  } catch (e) { if (!silent) alert('IA: ' + e.message); } finally { busy(btn, false); }
}
function manuscriptMarkdown() {
  return SECTION_ORDER.map((sec) => {
    const body = S.manuscript[sec] || '';
    return sec === 'title' ? `# ${body}\n` : `## ${SECTION_TITLES[sec]}\n\n${body}\n`;
  }).join('\n');
}
$('copyAll').onclick = (e) => copy(manuscriptMarkdown(), e.target);
$('dlMd').onclick = () => downloadText('manuscrito_metaforge.md', manuscriptMarkdown(), 'text/markdown');

// ---------- downloads ----------
$('dlForest').onclick = () => S.result && downloadText('forest.svg', S.result.forest_svg, 'image/svg+xml');
$('dlFunnel').onclick = () => S.result && downloadText('funnel.svg', S.result.funnel_svg, 'image/svg+xml');
$('dlCsv').onclick = () => {
  if (!S.result) return;
  const header = 'study_label,subgroup,estimate,ci_low,ci_high,weight_pct,yi,se\n';
  const lines = S.result.studies.map((s) => `"${s.label}",${s.subgroup || ''},${s.estimate},${s.ci_low},${s.ci_high},${s.weight_pct},${s.yi},${s.se}`).join('\n');
  downloadText('metaforge_estimates.csv', header + lines, 'text/csv');
};

init();

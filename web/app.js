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
  if (n === 8 && S.result && !Object.keys(S.manuscript).length) $('draftBtn').click();
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
  setStepEnabled(2, true); setStepEnabled(3, true); setStepEnabled(4, true); markDone(1);
  prepareProtocolStep(); prepareDataStep();
  goStep(2);
}
$('skipToData').onclick = () => {
  S.chosen = null; S.questionText = ''; S.measure = 'OR';
  setStepEnabled(3, true); setStepEnabled(4, true); markDone(1); prepareSearchStep(); prepareDataStep(); goStep(4);
};
$('demoBtn').onclick = async () => {
  const btn = $('demoBtn'); busy(btn, true, 'Cargando ejemplo…');
  try {
    const st = await (await fetch('/demo')).json();
    await restoreState(st);
    setProjStatus('Ejemplo cargado — explora los 8 pasos', true);
  } catch (e) { alert('No se pudo cargar el ejemplo: ' + e.message); } finally { busy(btn, false); }
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
$('toSearch').onclick = () => { prepareSearchStep(); goStep(3); };

// ---------- STEP 3: search & screening ----------
function stripTags(q) { return (q || '').replace(/\[[^\]]*\]/g, '').replace(/\s+/g, ' ').trim(); }
function prepareSearchStep() {
  if (!$('searchQ').value && S.protocol && S.protocol.search_pubmed) {
    $('searchQ').value = stripTags(S.protocol.search_pubmed);
  } else if (!$('searchQ').value && S.questionText) {
    $('searchQ').value = S.questionText.replace(/[¿?]/g, '').trim();
  }
}
function inclusionList() { return (S.protocol && S.protocol.inclusion_criteria) || []; }
function exclusionList() { return (S.protocol && S.protocol.exclusion_criteria) || []; }
$('searchBtn').onclick = async () => {
  $('searchErr').textContent = '';
  const query = $('searchQ').value.trim();
  if (!query) { $('searchErr').textContent = 'Escribe una consulta.'; return; }
  const btn = $('searchBtn'); busy(btn, true, 'Buscando…');
  try {
    const r = await fetch('/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, source: $('searchSource').value, page_size: Number($('searchN').value), only_oa: $('searchOA').checked, pubmed_query: (S.protocol || {}).search_pubmed || null }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error de búsqueda');
    S.searchMeta = data; S.searchDuplicates = data.duplicates_removed || 0;
    S.searchRecords = data.records.map((x) => ({ ...x, decision: null, reason: '' }));
    renderSearchMeta(data); renderResults();
    $('screenCard').style.display = '';
  } catch (e) { $('searchErr').textContent = e.message; } finally { busy(btn, false); }
};
function renderSearchMeta(d) {
  const parts = [];
  if (d.hit_europepmc != null) parts.push(`Europe PMC: <b>${d.hit_europepmc.toLocaleString()}</b>`);
  if (d.pubmed_count != null) parts.push(`PubMed (MeSH): <b>${d.pubmed_count.toLocaleString()}</b>`);
  let s = parts.join(' · ');
  if (d.duplicates_removed) s += ` · ${d.duplicates_removed} duplicado(s) eliminado(s)`;
  $('searchMeta').innerHTML = `${s}. Mostrando <b>${d.returned}</b> registros (orden por relevancia).`;
}
const DEC_LABEL = { include: 'Incluir', exclude: 'Excluir', maybe: 'Quizá', null: '—' };
function renderResults() {
  const recs = S.searchRecords || [];
  const rows = recs.map((r, i) => {
    const oa = r.is_oa ? '<span class="badge measure" style="background:#def7e8;color:#15803d;border-color:#bce9cf">OA</span>' : '';
    const link = r.pdf_url ? `<a class="link" href="${r.pdf_url}" target="_blank" rel="noopener">PDF</a>` : (r.doi_url ? `<a class="link" href="${r.doi_url}" target="_blank" rel="noopener">DOI</a>` : '');
    const conflict = r.decision2 && !r.agree;
    const decClass = conflict ? 'dec-conflict' : r.decision === 'include' ? 'dec-inc' : r.decision === 'exclude' ? 'dec-exc' : r.decision === 'maybe' ? 'dec-may' : '';
    const sel = ['include', 'maybe', 'exclude'].map((d) => `<option value="${d}"${r.decision === d ? ' selected' : ''}>${DEC_LABEL[d]}</option>`).join('');
    return `<tr class="${decClass}">
      <td><div style="font-weight:600">${esc(r.title)}</div><div class="muted" style="font-size:11.5px">${esc(r.authors.slice(0, 70))} · ${esc(r.journal)} ${esc(String(r.year))} ${oa}</div>
        ${r.abstract ? `<details><summary class="link" style="font-size:11.5px">resumen</summary><div class="muted" style="font-size:12px;margin-top:4px">${esc(r.abstract.slice(0, 800))}…</div></details>` : ''}
        ${r.reason ? `<div class="muted" style="font-size:11.5px;margin-top:3px">🤖 ${esc(r.reason)}</div>` : ''}
        ${conflict ? `<div style="font-size:11.5px;margin-top:3px;color:var(--warn)">⚠ Revisor 2: <b>${DEC_LABEL[r.decision2]}</b> — ${esc(r.reason2 || '')}</div>` : ''}</td>
      <td style="white-space:nowrap"><select data-dec="${i}">${sel}<option value=""${r.decision ? '' : ' selected'}>—</option></select></td>
      <td style="white-space:nowrap">${link}</td></tr>`;
  }).join('');
  $('resultsTable').innerHTML = `<tr><th>Artículo</th><th>Decisión</th><th></th></tr>${rows}`;
  $('resultsTable').querySelectorAll('[data-dec]').forEach((s) => { s.onchange = () => { S.searchRecords[Number(s.dataset.dec)].decision = s.value || null; renderResults(); updateScreenCounts(); }; });
  updateScreenCounts();
}
function updateScreenCounts() {
  const recs = S.searchRecords || [];
  const c = { include: 0, exclude: 0, maybe: 0, none: 0 };
  recs.forEach((r) => c[r.decision || 'none']++);
  $('screenCounts').textContent = `${recs.length} registros · ${c.include} incluir · ${c.maybe} quizá · ${c.exclude} excluir`;
}
$('screenBtn').onclick = async () => {
  const recs = S.searchRecords || [];
  if (!recs.length) return;
  const dual = $('dualScreen').checked;
  const btn = $('screenBtn'); btn.disabled = true;
  const chunk = dual ? 6 : 8; let failures = 0;
  for (let i = 0; i < recs.length; i += chunk) {
    btn.innerHTML = `<span class="spinner"></span> ${dual ? '2× ' : ''}Cribando ${Math.min(i + chunk, recs.length)}/${recs.length}…`;
    const slice = recs.slice(i, i + chunk).map((r) => ({ id: r.id, title: r.title, abstract: r.abstract }));
    try {
      const r = await fetch('/screen', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: slice, inclusion: inclusionList(), exclusion: exclusionList(), mode: 'auto', dual }) });
      const data = await r.json();
      (data.decisions || []).forEach((d) => { const rec = recs.find((x) => String(x.id) === String(d.id)); if (rec) { rec.decision = d.decision; rec.reason = d.reason; rec.decision2 = d.decision2 || null; rec.reason2 = d.reason2 || ''; rec.agree = d.agree !== false; } });
    } catch (e) { failures++; }
    renderResults();
  }
  btn.disabled = false; btn.innerHTML = '✦ Cribar con IA';
  if (dual) updateKappa(); else $('kappaBox').textContent = '';
  if (failures) setProjStatus(`${failures} lote(s) sin cribar; reintenta`, false);
};
function cohenKappa(a, b) {
  const n = a.length; if (!n) return null;
  const cats = [...new Set([...a, ...b])];
  let po = 0; for (let i = 0; i < n; i++) if (a[i] === b[i]) po++; po /= n;
  let pe = 0; cats.forEach((c) => { pe += (a.filter((x) => x === c).length / n) * (b.filter((x) => x === c).length / n); });
  return pe >= 1 ? 1 : Math.round((po - pe) / (1 - pe) * 1000) / 1000;
}
function kappaLabel(k) { return k < 0.2 ? 'pobre' : k < 0.4 ? 'débil' : k < 0.6 ? 'moderada' : k < 0.8 ? 'buena' : 'muy buena'; }
function updateKappa() {
  const recs = (S.searchRecords || []).filter((r) => r.decision2);
  if (recs.length < 2) { $('kappaBox').textContent = ''; return; }
  const k = cohenKappa(recs.map((r) => r.decision), recs.map((r) => r.decision2));
  const conflicts = recs.filter((r) => !r.agree).length;
  $('kappaBox').innerHTML = `Concordancia entre revisores IA: <b>κ = ${k}</b> (${kappaLabel(k)}). <b>${conflicts}</b> conflicto(s) a resolver (resaltados en naranja).`;
}
$('extractBtn').onclick = async () => {
  const incl = (S.searchRecords || []).filter((r) => r.decision === 'include');
  if (!incl.length) { alert('Marca artículos como «Incluir» primero.'); return; }
  if (S.measure === 'GEN') { alert('Define una medida de efecto (no GEN) para extraer datos.'); return; }
  const btn = $('extractBtn'); btn.disabled = true;
  const outcome = (S.protocol && S.protocol.outcomes && S.protocol.outcomes[0]) || '';
  const rows = []; let found = 0;
  for (let i = 0; i < incl.length; i++) {
    btn.innerHTML = `<span class="spinner"></span> Extrayendo ${i + 1}/${incl.length}…`;
    try {
      const r = await fetch('/extract', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ record: incl[i], measure: S.measure, outcome, mode: 'auto' }) });
      const data = await r.json(); rows.push(data); if (data.found) found++;
    } catch (e) { /* skip */ }
  }
  btn.disabled = false; btn.innerHTML = '✦ Extraer datos de incluidos (IA)';
  if (rows.length) {
    const fields = Object.keys(rows[0].fields);
    $('csv').value = `study_label,effect_measure,${fields.join(',')}\n` + rows.map((r) => r.csv_row).join('\n');
    setProjStatus(`Extraídos ${found}/${incl.length}; revisa y completa en Datos`, true);
    prepareDataStep(); goStep(4);
  }
};
// Comprehensive extraction → Excel: reads tables, text, figure captions AND the
// figure images of every included open-access article and fills a workbook with
// everything, ready for the meta-analysis. Each article is fanned out into small
// parallel AI calls server-side, so it is thorough without timing out.
$('extractExcelBtn').onclick = async () => {
  const incl = (S.searchRecords || []).filter((r) => r.decision === 'include');
  if (!incl.length) { alert('Marca artículos como «Incluir» primero.'); return; }
  const btn = $('extractExcelBtn'); btn.disabled = true;
  const status = $('excelStatus');
  const extractions = []; let outcomes = 0, noFull = 0, figs = 0; const metaRows = [];
  for (let i = 0; i < incl.length; i++) {
    btn.innerHTML = `<span class="spinner"></span> Extrayendo ${i + 1}/${incl.length}…`;
    status.textContent = `Leyendo tablas, texto, pies y las imágenes de las figuras del artículo ${i + 1} de ${incl.length}… (puede tardar ~1–2 min por artículo)`;
    try {
      const r = await fetch('/extract/full', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ record: incl[i], mode: 'auto' }) });
      const data = await r.json();
      extractions.push(data);
      if (data.data) outcomes += (data.data.outcomes || []).length;
      if (data.n_figures) figs += data.n_figures;
      if (data.meta_rows) metaRows.push(...data.meta_rows);
      if (!data.has_fulltext) noFull++;
    } catch (e) { extractions.push({ study_label: `${(incl[i].authors || '').split(',')[0]} ${incl[i].year}`, data: null, note: 'Error: ' + e.message }); }
  }
  btn.disabled = false; btn.innerHTML = '✦ Extraer TODO a Excel (IA)';
  try {
    const r = await fetch('/extract/excel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ extractions }) });
    const blob = await r.blob();
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'extraccion_metaforge.xlsx'; a.click(); URL.revokeObjectURL(a.href);
    const warn = noFull ? ` · ${noFull} sin texto de acceso abierto (sólo resumen)` : '';
    const figNote = figs ? ` · ${figs} figuras leídas (datos aprox. marcados aparte)` : '';
    const loadBtn = metaRows.length ? ` <button class="btn btn-sm btn-primary" id="loadMetaBtn">Cargar ${metaRows.length} filas al paso Datos →</button>` : '';
    status.innerHTML = `✓ Excel generado: <b>${incl.length}</b> estudios · <b>${outcomes}</b> desenlaces${figNote}${warn}. Revisa siempre contra la fuente antes de sintetizar.${loadBtn}`;
    S.fullExtractions = extractions; S.metaRows = metaRows;
    if (metaRows.length) $('loadMetaBtn').onclick = () => loadMetaRowsToData(metaRows);
  } catch (e) { status.textContent = 'No se pudo generar el Excel: ' + e.message; }
};
// Load the meta-analysis-ready rows straight into the Data step CSV — no Excel
// round-trip. Rows are sorted by outcome so the same outcome sits together; the
// epidemiologist keeps one outcome+measure and runs the synthesis.
const META_COLS = ['study_label', 'year', 'outcome', 'effect_measure',
  'a_events', 'b_non_events', 'c_events', 'd_non_events',
  'n_intervention', 'mean_intervention', 'sd_intervention',
  'n_control', 'mean_control', 'sd_control',
  'events_intervention', 'time_intervention', 'events_control', 'time_control',
  'effect_value', 'ci_lower_95', 'ci_upper_95'];
function metaRowsToCsv(rows) {
  const cell = (v) => (v === null || v === undefined || v === '') ? '' : String(v);
  return [META_COLS.join(',')].concat(rows.map((r) => META_COLS.map((c) => cell(r[c])).join(','))).join('\n');
}
// Group loaded rows by outcome × measure so the epidemiologist can isolate the
// single outcome+measure to pool. Same-named outcomes across studies group
// together; that group is what becomes one meta-analysis.
function outcomeGroups(rows) {
  const groups = new Map();
  rows.forEach((r) => {
    const key = `${(r.outcome || '(sin nombre)').trim()} · ${r.effect_measure}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(r);
  });
  return groups;
}
function populateOutcomeFilter(rows) {
  const sel = $('outcomeFilter'); const wrap = $('outcomeFilterRow');
  const groups = outcomeGroups(rows);
  if (groups.size <= 1) { wrap.style.display = 'none'; return; }
  const opts = [`<option value="__all">Todos los desenlaces (${rows.length} filas)</option>`];
  // most studies first — the most poolable outcome floats to the top
  [...groups.entries()].sort((a, b) => b[1].length - a[1].length)
    .forEach(([k, rs]) => opts.push(`<option value="${k.replace(/"/g, '&quot;')}">${k} — ${rs.length} estudio(s)</option>`));
  sel.innerHTML = opts.join('');
  wrap.style.display = '';
  sel.onchange = () => {
    const chosen = sel.value === '__all' ? rows : (groups.get(sel.value) || rows);
    $('csv').value = metaRowsToCsv(chosen);
    updateDataStatus();
  };
}
function loadMetaRowsToData(rows) {
  const sorted = [...rows].sort((a, b) => String(a.outcome || '').localeCompare(String(b.outcome || '')) || String(a.effect_measure).localeCompare(String(b.effect_measure)));
  $('csv').value = metaRowsToCsv(sorted);
  prepareDataStep();
  populateOutcomeFilter(sorted);
  goStep(4); updateDataStatus();
  const groups = outcomeGroups(sorted);
  const top = [...groups.entries()].sort((a, b) => b[1].length - a[1].length)[0];
  const hint = groups.size > 1
    ? `Cargadas ${rows.length} filas con ${groups.size} desenlaces. Elige uno arriba (sugerido: «${top[0]}», ${top[1].length} estudios) y pulsa Analizar.`
    : `Cargadas ${rows.length} filas. Revisa y pulsa Analizar.`;
  setProjStatus(hint, true);
}
// Live read-out of how many usable study rows the CSV holds.
function updateDataStatus() {
  const el = $('dataStatus'); if (!el) return;
  const lines = ($('csv').value || '').trim().split('\n').filter((l) => l.trim());
  const n = Math.max(0, lines.length - 1);
  el.textContent = n ? `${n} estudio(s) en la tabla` : '';
}
function includedRecords() {
  const incl = (S.searchRecords || []).filter((r) => r.decision === 'include');
  if (!incl.length) alert('No hay artículos marcados como «Incluir».');
  return incl;
}
$('exportIncl').onclick = () => {
  const incl = includedRecords(); if (!incl.length) return;
  const header = 'study_label,year,doi,pmid,title,journal\n';
  const lines = incl.map((r) => `"${(r.authors.split(',')[0] || 'Estudio')} ${r.year}",${r.year},${r.doi || ''},${r.pmid || ''},"${r.title.replace(/"/g, "'")}","${r.journal}"`).join('\n');
  downloadText('estudios_incluidos.csv', header + lines, 'text/csv');
};
async function exportCitations(format) {
  const incl = includedRecords(); if (!incl.length) return;
  const r = await fetch('/citations/export', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: incl, format }) });
  const blob = await r.blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `referencias.${format === 'bibtex' ? 'bib' : 'ris'}`; a.click(); URL.revokeObjectURL(a.href);
}
$('exportRis').onclick = () => exportCitations('ris');
$('exportBib').onclick = () => exportCitations('bibtex');

// import RIS/BibTeX -> records to screen
$('importBtn').onclick = () => $('importFile').click();
$('importFile').onchange = async (e) => {
  const file = e.target.files[0]; if (!file) return;
  const text = await file.text();
  try {
    const r = await fetch('/citations/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
    const data = await r.json();
    if (!data.count) { alert('No se reconocieron referencias en el archivo.'); return; }
    S.searchRecords = data.records.map((x) => ({ ...x, decision: null, reason: '' }));
    S.searchMeta = { hit_count: data.count, returned: data.count, hit_europepmc: null, pubmed_count: null, duplicates_removed: 0 };
    $('searchMeta').innerHTML = `Importadas <b>${data.count}</b> referencias desde archivo.`;
    renderResults(); $('screenCard').style.display = '';
  } catch (err) { alert('No se pudo importar: ' + err.message); }
  e.target.value = '';
};

// Zotero
$('zoteroBtn').onclick = async () => {
  const box = $('zoteroCfg');
  box.style.display = box.style.display === 'none' ? 'block' : 'none';
  $('zoteroKey').value = localStorage.getItem('mf_zotero_key') || '';
  $('zoteroUser').value = localStorage.getItem('mf_zotero_user') || '';
  if (box.style.display !== 'none') {
    $('zoteroLocalStatus').textContent = 'comprobando…';
    try {
      const s = await (await fetch('/zotero/local-status')).json();
      $('zoteroLocal').disabled = !s.available;
      $('zoteroLocalStatus').textContent = s.available ? 'Zotero detectado ✓' : 'Zotero de escritorio no detectado (ábrelo y reintenta)';
    } catch { $('zoteroLocalStatus').textContent = ''; }
  }
};
$('zoteroLocal').onclick = async () => {
  const incl = includedRecords(); if (!incl.length) return;
  const btn = $('zoteroLocal'); busy(btn, true, 'Enviando…');
  try {
    const r = await fetch('/zotero/local-push', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: incl }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    $('zoteroStatus').innerHTML = `✓ Enviadas <b>${data.created}</b> referencias a Zotero de escritorio.`;
  } catch (e) { $('zoteroStatus').textContent = 'Error: ' + e.message; } finally { busy(btn, false); }
};
$('zoteroPush').onclick = async () => {
  const incl = includedRecords(); if (!incl.length) return;
  const api_key = $('zoteroKey').value.trim(), user_id = $('zoteroUser').value.trim();
  if (!api_key || !user_id) { $('zoteroStatus').textContent = 'Falta la clave o el ID.'; return; }
  localStorage.setItem('mf_zotero_key', api_key); localStorage.setItem('mf_zotero_user', user_id);
  const btn = $('zoteroPush'); busy(btn, true, 'Enviando…');
  try {
    const r = await fetch('/zotero/push', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: incl, api_key, user_id, collection: $('zoteroColl').value.trim() || null }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    $('zoteroStatus').innerHTML = `✓ Enviadas <b>${data.created}</b> referencias a Zotero${data.collection ? ` (colección «${esc(data.collection)}»)` : ''}.${data.failed ? ` ${data.failed} fallaron.` : ''}`;
  } catch (e) { $('zoteroStatus').textContent = 'Error: ' + e.message; } finally { busy(btn, false); }
};
$('fillPrisma').onclick = () => {
  const recs = S.searchRecords || [];
  const incl = recs.filter((r) => r.decision === 'include').length;
  const exc = recs.filter((r) => r.decision === 'exclude').length;
  const maybe = recs.filter((r) => r.decision === 'maybe').length;
  if (S.searchMeta) $('pf_identified_db').value = S.searchMeta.hit_count;
  if (S.searchDuplicates != null) $('pf_duplicates').value = S.searchDuplicates;
  $('pf_screened').value = recs.length;
  $('pf_excluded_screen').value = exc;
  $('pf_sought').value = incl + maybe;
  $('pf_fulltext_assessed').value = incl + maybe;
  $('pf_included').value = incl;
  setProjStatus('Conteos volcados a PRISMA (paso Calidad)', true);
};
function prepareDataFromSearch() {
  const incl = (S.searchRecords || []).filter((r) => r.decision === 'include');
  if (incl.length && !$('csv').value.trim()) {
    const kind = MEASURE_KIND[S.measure] || '2x2';
    const cols = KIND_COLS[kind].split(', ').slice(2);  // drop study_label, effect_measure
    const header = `study_label,effect_measure,${cols.join(',')}\n`;
    const rows = incl.map((r) => `"${(r.authors.split(',')[0] || 'Estudio')} ${r.year}",${S.measure},${cols.map(() => '').join(',')}`).join('\n');
    $('csv').value = header + rows;
  }
}
$('fulltextBtn').onclick = async () => {
  const recs = (S.searchRecords || []).filter((r) => ['include', 'maybe'].includes(r.decision));
  if (!recs.length) { alert('Primero criba por título/resumen y marca candidatos (incluir/quizá).'); return; }
  const btn = $('fulltextBtn'); btn.disabled = true;
  for (let i = 0; i < recs.length; i++) {
    btn.innerHTML = `<span class="spinner"></span> Texto completo ${i + 1}/${recs.length}…`;
    try {
      const r = await fetch('/screen/fulltext', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ record: recs[i], inclusion: inclusionList(), exclusion: exclusionList(), mode: 'auto' }) });
      const d = await r.json();
      const rec = (S.searchRecords || []).find((x) => String(x.id) === String(d.id));
      if (rec) { rec.decision = d.decision; rec.reason = '[Texto completo] ' + (d.reason || ''); rec.phase = 'fulltext'; }
    } catch (e) { /* skip */ }
    renderResults();
  }
  btn.disabled = false; btn.innerHTML = 'Texto completo';
};
$('toData').onclick = () => { prepareDataFromSearch(); goStep(4); };

// ---------- STEP 4: data ----------
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
  $('outcomeFilterRow').style.display = 'none';
  if (data.favours_low) S.flow = data.favours_low;
  if (data.favours_high) S.fhigh = data.favours_high;
  updateDataStatus();
};
$('clearData').onclick = () => { $('csv').value = ''; $('outcomeFilterRow').style.display = 'none'; updateDataStatus(); };
$('csv').addEventListener('input', updateDataStatus);
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
    setStepEnabled(5, true); setStepEnabled(6, true); setStepEnabled(7, true); setStepEnabled(8, true);
    prepareQualityStep();
    markDone(4); $('noResult').style.display = 'none'; $('articleWrap').style.display = '';
    if (advance) goStep(5);
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
$('toDiag').onclick = () => goStep(6);
$('toQuality').onclick = () => goStep(7);
$('toArticle').onclick = () => goStep(8);

// ---------- STEP 6: quality (PRISMA + RoB) ----------
let ROB_TOOLS = {};
async function prepareQualityStep() {
  if (!Object.keys(ROB_TOOLS).length) {
    try { ROB_TOOLS = await (await fetch('/rob/tools')).json(); } catch { return; }
    const sel = $('robTool');
    sel.innerHTML = Object.entries(ROB_TOOLS).map(([k, v]) => `<option value="${k}">${esc(v.name)}</option>`).join('');
    sel.onchange = buildRobGrid;
  }
  buildRobGrid();
}
function robStudies() { return (S.result && S.result.studies) ? S.result.studies.map((s) => s.label) : []; }
function buildRobGrid() {
  const tool = $('robTool').value || 'rob2';
  const domains = (ROB_TOOLS[tool] || {}).domains || {};
  const codes = Object.keys(domains);
  const opts = (cur) => ['low', 'some', 'high', 'na'].map((r) => `<option value="${r}"${r === cur ? ' selected' : ''}>${{ low: 'Bajo', some: 'Dudas', high: 'Alto', na: 'Sin info.' }[r]}</option>`).join('');
  const head = `<tr><th>Estudio</th>${codes.map((c) => `<th title="${esc(domains[c])}">${c}</th>`).join('')}</tr>`;
  const rows = robStudies().map((st, i) => `<tr><td>${esc(st)}</td>${codes.map((c) => `<td><select data-rob="${i}" data-dom="${c}">${opts('low')}</select></td>`).join('')}</tr>`).join('');
  $('robGrid').innerHTML = head + rows;
}
function collectRob() {
  const ratings = {};
  const studies = robStudies();
  $('robGrid').querySelectorAll('select[data-rob]').forEach((s) => {
    const st = studies[Number(s.dataset.rob)];
    (ratings[st] = ratings[st] || {})[s.dataset.dom] = s.value;
  });
  return { studies, ratings };
}
$('prismaBtn').onclick = async () => {
  const form = collectPrismaForm();
  const counts = {};
  Object.entries(form).forEach(([k, v]) => { if (v !== '' && v != null) counts[k] = v; });
  const btn = $('prismaBtn'); busy(btn, true, 'Generando…');
  try {
    const r = await fetch('/prisma', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ counts, included_meta: S.result ? S.result.k : null }) });
    const data = await r.json();
    S.prismaSvg = data.svg;
    $('prismaPlot').innerHTML = data.svg; $('prismaPlot').style.display = ''; $('prismaDl').style.display = '';
  } catch (e) { alert(e.message); } finally { busy(btn, false); }
};
$('prismaDl').onclick = () => S.prismaSvg && downloadText('prisma.svg', S.prismaSvg, 'image/svg+xml');
$('robBtn').onclick = async () => {
  const { studies, ratings } = collectRob();
  if (!studies.length) { alert('Ejecuta el análisis primero para tener estudios.'); return; }
  const btn = $('robBtn'); busy(btn, true, 'Generando…');
  try {
    const r = await fetch('/rob', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ studies, ratings, tool: $('robTool').value }) });
    const data = await r.json();
    S.robSvg = data.svg;
    $('robPlot').innerHTML = data.svg; $('robPlot').style.display = ''; $('robDl').style.display = '';
  } catch (e) { alert(e.message); } finally { busy(btn, false); }
};
$('robDl').onclick = () => S.robSvg && downloadText('riesgo_sesgo.svg', S.robSvg, 'image/svg+xml');

// ---------- GRADE ----------
const GRADE_DOMS = ['risk_of_bias', 'inconsistency', 'indirectness', 'imprecision', 'publication_bias'];
const GRADE_LABELS = { risk_of_bias: 'Riesgo de sesgo', inconsistency: 'Inconsistencia', indirectness: 'Evidencia indirecta', imprecision: 'Imprecisión', publication_bias: 'Sesgo de publicación' };
const DOWN_OPTS = { none: 'No rebajar', serious: 'Serio (−1)', very_serious: 'Muy serio (−2)' };
const DOWN_VAL = { none: 0, serious: -1, very_serious: -2 };
const UP_DOMS = ['large_effect', 'dose_response', 'confounding'];
const UP_LABELS = { large_effect: 'Magnitud del efecto', dose_response: 'Gradiente dosis-respuesta', confounding: 'Confusión residual' };
const UP_OPTS = {
  large_effect: { none: 'Sin ajuste', large: 'Grande (+1)', very_large: 'Muy grande (+2)' },
  dose_response: { none: 'Sin ajuste', yes: 'Presente (+1)' },
  confounding: { none: 'Sin ajuste', yes: 'Subestima el efecto (+1)' },
};
const UP_VAL = { none: 0, yes: 1, large: 1, very_large: 2 };
const CERT_LABEL = { 4: 'Alta', 3: 'Moderada', 2: 'Baja', 1: 'Muy baja' };
function computeCertainty(design, downgrades, upgrades) {
  let total = design === 'rct' ? 4 : 2;
  GRADE_DOMS.forEach((d) => { total += DOWN_VAL[downgrades[d] || 'none']; });
  if (design !== 'rct' && upgrades) UP_DOMS.forEach((u) => { total += UP_VAL[upgrades[u] || 'none']; });
  const level = Math.max(1, Math.min(4, total));
  return { level, label: CERT_LABEL[level] };
}
$('gradeBtn').onclick = async () => {
  if (!S.result) { alert('Ejecuta el análisis primero.'); return; }
  const rob = collectRob(); rob.tool = $('robTool').value;
  const btn = $('gradeBtn'); busy(btn, true, 'Evaluando…');
  try {
    const r = await fetch('/grade', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ result: S.result, design: $('gradeDesign').value, rob }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    S.grade = data; renderGrade(data);
  } catch (e) { alert(e.message); } finally { busy(btn, false); }
};
$('gradeDesign').onchange = () => { if (S.grade && S.grade.domains) renderGrade(S.grade); };
function renderGrade(g) {
  g.domains = g.domains || {}; g.upgrades = g.upgrades || {};
  const design = $('gradeDesign').value;
  const downRows = GRADE_DOMS.map((d) => {
    const info = g.domains[d] || { rating: 'none', reason: '' };
    const opts = Object.entries(DOWN_OPTS).map(([v, l]) => `<option value="${v}"${v === info.rating ? ' selected' : ''}>${l}</option>`).join('');
    return `<div class="grade-row"><b>${GRADE_LABELS[d]}</b><select data-gd="${d}">${opts}</select><span class="reason">${esc(info.reason)}</span></div>`;
  }).join('');
  let upBlock = '';
  if (design !== 'rct') {
    const upRows = UP_DOMS.map((u) => {
      const cur = g.upgrades[u] || 'none';
      const opts = Object.entries(UP_OPTS[u]).map(([v, l]) => `<option value="${v}"${v === cur ? ' selected' : ''}>${l}</option>`).join('');
      return `<div class="grade-row"><b>${UP_LABELS[u]}</b><select data-gu="${u}">${opts}</select><span class="reason">Subir certeza (solo evidencia observacional)</span></div>`;
    }).join('');
    upBlock = `<p class="sub" style="margin-top:14px">Subir certeza</p>${upRows}`;
  }
  $('gradeBody').innerHTML = `<div id="gradeCertBox"></div><p class="sub">Bajar certeza</p>${downRows}${upBlock}`;
  $('gradeBody').querySelectorAll('[data-gd]').forEach((s) => { s.onchange = () => { (S.grade.domains[s.dataset.gd] = S.grade.domains[s.dataset.gd] || {}).rating = s.value; recomputeGrade(); }; });
  $('gradeBody').querySelectorAll('[data-gu]').forEach((s) => { s.onchange = () => { S.grade.upgrades[s.dataset.gu] = s.value; recomputeGrade(); }; });
  recomputeGrade();
}
function recomputeGrade() {
  const design = $('gradeDesign').value;
  const dg = {}; GRADE_DOMS.forEach((d) => { dg[d] = (S.grade.domains[d] || {}).rating || 'none'; });
  const c = computeCertainty(design, dg, S.grade.upgrades); S.grade.certainty = c; S.grade.design = design;
  const pips = '⊕'.repeat(c.level) + '⊝'.repeat(4 - c.level);
  $('gradeCertBox').innerHTML = `<div class="grade-cert l${c.level}"><span class="grade-pips">${pips}</span> Certeza de la evidencia: ${c.label} (${c.level}/4)</div>`;
  clearTimeout(S._sofTimer); S._sofTimer = setTimeout(refreshSof, 400);
}
async function refreshSof() {
  if (!S.result || !S.grade) return;
  const outcome = (S.chosen && S.chosen.outcome) || 'Desenlace principal';
  try {
    const r = await fetch('/grade/sof', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ result: S.result, grade: S.grade, outcome }) });
    const data = await r.json(); if (!r.ok) return;
    S.sofSvg = data.svg;
    $('sofBox').innerHTML = `<div class="plot">${data.svg}</div><a class="link" id="dlSof">descargar tabla SoF (SVG)</a>`;
    $('dlSof').onclick = () => downloadText('resumen_hallazgos_grade.svg', S.sofSvg, 'image/svg+xml');
  } catch (e) { /* non-blocking */ }
}

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
  populateModerators();
}

// ---------- Meta-regression ----------
const _NON_MOD = new Set(['study_label', 'label', 'effect_measure', 'outcome_type', 'subgroup', 'group', 'authors', 'design', 'doi', 'pmid', 'notes', 'a_events', 'b_non_events', 'c_events', 'd_non_events']);
function detectModerators() {
  const text = $('csv').value.trim(); if (!text) return [];
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
  const rows = lines.slice(1).map((l) => l.split(','));
  const out = [];
  headers.forEach((h, i) => {
    if (_NON_MOD.has(h) || !h) return;
    let numeric = 0;
    rows.forEach((r) => { const v = (r[i] || '').trim(); if (v !== '' && !Number.isNaN(Number(v))) numeric++; });
    if (numeric >= 3) out.push(h);
  });
  return out;
}
function populateModerators() {
  const mods = detectModerators();
  const sel = $('modSel');
  if (!mods.length) { sel.innerHTML = '<option value="">(añade una columna numérica)</option>'; $('metaregBtn').disabled = true; return; }
  sel.innerHTML = mods.map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join('');
  $('metaregBtn').disabled = false;
}
$('metaregBtn').onclick = async () => {
  const moderator = $('modSel').value; if (!moderator) return;
  const btn = $('metaregBtn'); busy(btn, true, 'Calculando…');
  try {
    const r = await fetch('/meta-regression', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ csv: $('csv').value, moderator, knapp_hartung: $('kh').checked }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    renderMetareg(data, moderator);
  } catch (e) { $('metaregBody').innerHTML = `<div class="error">${esc(e.message)}</div>`; } finally { busy(btn, false); }
};
function renderMetareg(d, moderator) {
  const s = d.slice ? d.slice : d.slope;
  const sig = d.slope.p_value < 0.05;
  const interp = sig
    ? `<b>${esc(moderator)} se asocia con el efecto</b> (pendiente ${fmt(d.slope.estimate, 3)}, p=${fmt(d.slope.p_value, 3)}); explica ≈${fmt(d.r2, 0)}% de la heterogeneidad.`
    : `No hay evidencia de que <b>${esc(moderator)}</b> modere el efecto (pendiente ${fmt(d.slope.estimate, 3)}, p=${fmt(d.slope.p_value, 3)}).`;
  const scaleNote = d.log_scale ? ' (escala log del efecto)' : '';
  $('metaregBody').innerHTML = `
    <div class="interp">${interp}</div>
    <table style="max-width:520px">
      <tr><th>Término</th><th>Coef.${scaleNote}</th><th>IC 95%</th><th>p</th></tr>
      <tr><td>Intercepto</td><td>${fmt(d.intercept.estimate, 3)}</td><td>[${fmt(d.intercept.ci_low, 3)}, ${fmt(d.intercept.ci_high, 3)}]</td><td>${fmt(d.intercept.p_value, 3)}</td></tr>
      <tr><td>${esc(moderator)}</td><td>${fmt(d.slope.estimate, 3)}</td><td>[${fmt(d.slope.ci_low, 3)}, ${fmt(d.slope.ci_high, 3)}]</td><td>${fmt(d.slope.p_value, 3)}</td></tr>
    </table>
    <p class="muted" style="margin-top:8px">R²=${fmt(d.r2, 0)}% de τ² explicado · τ² residual=${fmt(d.tau2_residual, 4)} · Q residual p=${fmt(d.qe_p, 3)} · ${d.knapp_hartung ? 'prueba t (Knapp-Hartung)' : 'prueba z'} · k=${d.k}</p>
    <div class="plot" style="margin-top:10px">${d.bubble_svg}</div>`;
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
function mdInline(s) { return s.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, '<em>$1</em>'); }
function mdToHtml(md) {
  return String(md || '').split(/\n{2,}/).map((block) => {
    const lines = block.split('\n');
    if (lines.length && lines.every((l) => /^\s*[-*]\s+/.test(l))) {
      return '<ul>' + lines.map((l) => `<li>${mdInline(esc(l.replace(/^\s*[-*]\s+/, '')))}</li>`).join('') + '</ul>';
    }
    const h = block.match(/^(#{2,4})\s+(.*)$/);
    if (h && lines.length === 1) { const lvl = h[1].length + 1; return `<h${lvl}>${mdInline(esc(h[2]))}</h${lvl}>`; }
    return `<p>${lines.map((l) => mdInline(esc(l))).join('<br>')}</p>`;
  }).join('');
}
function renderSections() {
  const editable = !S.preview;
  $('sections').innerHTML = SECTION_ORDER.map((sec) => {
    const body = S.manuscript[sec] || '';
    const content = editable
      ? `<textarea data-ta="${sec}">${esc(body)}</textarea>`
      : `<div class="sec-preview rc-markdown">${body.trim() ? mdToHtml(body) : '<span class="muted">(vacío)</span>'}</div>`;
    return `<div class="sec" data-sec="${sec}">
      <div class="sec-head"><h4>${SECTION_TITLES[sec]}</h4>
        <div class="sec-actions">${S.ai ? `<button class="btn btn-mini" data-ai="${sec}">✦ Mejorar con IA</button>` : ''}<button class="btn btn-mini" data-copy="${sec}">Copiar</button></div>
      </div>${content}</div>`;
  }).join('');
  if (editable) $('sections').querySelectorAll('textarea').forEach((ta) => { autoGrow(ta); ta.oninput = () => { S.manuscript[ta.dataset.ta] = ta.value; autoGrow(ta); }; });
  $('sections').querySelectorAll('[data-copy]').forEach((b) => { b.onclick = () => copy(S.manuscript[b.dataset.copy] || '', b); });
  $('sections').querySelectorAll('[data-ai]').forEach((b) => { b.onclick = () => improveSection(b.dataset.ai, b); });
}
$('previewToggle').onclick = () => { S.preview = !S.preview; $('previewToggle').textContent = S.preview ? '✎ Editar' : '👁 Vista previa'; renderSections(); };
async function improveSection(sec, btn, silent) {
  busy(btn, true, 'IA…');
  try {
    const r = await fetch('/manuscript/section', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: questionForArticle(), result: S.result, section: sec, protocol: S.protocol, mode: 'ai' }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error');
    S.manuscript[sec] = data.text;
    if (S.preview) { renderSections(); } else { const ta = $('sections').querySelector(`[data-ta="${sec}"]`); if (ta) { ta.value = data.text; autoGrow(ta); } }
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
$('dlDocx').onclick = async (e) => {
  const btn = e.target; busy(btn, true, 'Word…');
  try {
    const figures = { forest: S.result && S.result.forest_svg, funnel: S.result && S.result.funnel_svg, prisma: S.prismaSvg, rob: S.robSvg, sof: S.sofSvg };
    const r = await fetch('/manuscript/docx', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sections: S.manuscript, facts: $('facts').textContent, figures, grade: S.grade }) });
    if (!r.ok) throw new Error('No se pudo generar el Word');
    const blob = await r.blob();
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'manuscrito_metaforge.docx'; a.click(); URL.revokeObjectURL(a.href);
  } catch (err) { alert(err.message); } finally { busy(btn, false); }
};
$('printPdf').onclick = () => {
  const html = SECTION_ORDER.map((sec) => {
    const body = esc(S.manuscript[sec] || '').replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^## (.+)$/gm, '<h3>$1</h3>').replace(/\n/g, '<br>');
    return sec === 'title' ? `<h1>${body}</h1>` : `<h2>${SECTION_TITLES[sec]}</h2><p>${body}</p>`;
  }).join('');
  const w = window.open('', '_blank');
  w.document.write(`<html><head><title>Manuscrito</title><style>body{font-family:Georgia,serif;max-width:720px;margin:40px auto;line-height:1.7;color:#1a1a22}h1{font-size:22px}h2{font-size:17px;margin-top:24px}h3{font-size:14px}</style></head><body>${html}</body></html>`);
  w.document.close(); w.focus(); setTimeout(() => w.print(), 300);
};

// ---------- downloads ----------
$('dlForest').onclick = () => S.result && downloadText('forest.svg', S.result.forest_svg, 'image/svg+xml');
$('dlFunnel').onclick = () => S.result && downloadText('funnel.svg', S.result.funnel_svg, 'image/svg+xml');
$('dlCsv').onclick = () => {
  if (!S.result) return;
  const header = 'study_label,subgroup,estimate,ci_low,ci_high,weight_pct,yi,se\n';
  const lines = S.result.studies.map((s) => `"${s.label}",${s.subgroup || ''},${s.estimate},${s.ci_low},${s.ci_high},${s.weight_pct},${s.yi},${s.se}`).join('\n');
  downloadText('metaforge_estimates.csv', header + lines, 'text/csv');
};

// ---------- Projects: save / resume ----------
const PRISMA_FIELDS = ['identified_db', 'identified_registers', 'identified_other', 'duplicates', 'screened', 'excluded_screen', 'sought', 'not_retrieved', 'fulltext_assessed', 'fulltext_excluded', 'included',
  'other_citation', 'other_websites', 'other_orgs', 'other_sought', 'other_not_retrieved', 'other_assessed', 'other_excluded'];
function collectPrismaForm() {
  const o = {}; PRISMA_FIELDS.forEach((k) => { const el = $('pf_' + k); if (el) o[k] = el.value; });
  o.exclusion_reasons = $('pf_exclusion_reasons').value;
  o.other_reasons = ($('pf_other_reasons') || {}).value || '';
  return o;
}
function collectState() {
  return {
    v: 2, step: S.step, topic: $('topic').value, questionText: S.questionText, measure: S.measure,
    chosen: S.chosen, questions: S.questions || [], protocol: S.protocol,
    csv: $('csv').value, model: $('model').value, tau2: $('tau2').value, kh: $('kh').checked,
    flow: $('flow').value, fhigh: $('fhigh').value,
    searchQ: $('searchQ').value, searchMeta: S.searchMeta, searchRecords: S.searchRecords,
    result: S.result, prisma: collectPrismaForm(), prismaSvg: S.prismaSvg,
    robTool: $('robTool').value, robRatings: collectRob().ratings, robSvg: S.robSvg,
    grade: S.grade, manuscript: S.manuscript, facts: $('facts').textContent,
  };
}
function setProjStatus(msg, ok) { const e = $('projStatus'); e.textContent = msg; e.className = 'proj-status' + (ok ? ' ok' : ''); if (ok) setTimeout(() => { e.textContent = ''; }, 2500); }
async function refreshProjects() {
  try {
    const { projects } = await (await fetch('/projects')).json();
    const sel = $('loadProj');
    sel.innerHTML = '<option value="">Cargar proyecto…</option>' + projects.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('');
  } catch {}
}
$('saveProj').onclick = async () => {
  const name = $('projName').value.trim() || 'Proyecto sin título';
  const btn = $('saveProj'); busy(btn, true, 'Guardando…');
  try {
    const r = await fetch('/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, state: collectState(), id: S.projectId || null }) });
    const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'Error');
    S.projectId = data.id; setProjStatus('Guardado ✓', true); await refreshProjects(); $('loadProj').value = data.id;
  } catch (e) { setProjStatus(e.message, false); } finally { busy(btn, false); }
};
$('loadProj').onchange = async (e) => {
  const id = e.target.value; if (!id) return;
  try {
    const rec = await (await fetch('/projects/' + id)).json();
    await restoreState(rec.state || {});
    S.projectId = rec.id; $('projName').value = rec.name || ''; setProjStatus('Cargado ✓', true);
  } catch (err) { setProjStatus('No se pudo cargar', false); }
};
$('delProj').onclick = async () => {
  if (!S.projectId) { setProjStatus('No hay proyecto cargado', false); return; }
  if (!confirm('¿Eliminar este proyecto guardado?')) return;
  await fetch('/projects/' + S.projectId, { method: 'DELETE' });
  S.projectId = null; setProjStatus('Eliminado', true); await refreshProjects();
};
function restoreRobRatings(ratings) {
  const studies = robStudies();
  $('robGrid').querySelectorAll('select[data-rob]').forEach((s) => {
    const st = studies[Number(s.dataset.rob)]; const v = (ratings[st] || {})[s.dataset.dom];
    if (v) s.value = v;
  });
}
async function restoreState(st) {
  $('topic').value = st.topic || ''; S.questionText = st.questionText || ''; S.measure = st.measure || 'OR';
  S.chosen = st.chosen || null; S.questions = st.questions || []; S.protocol = st.protocol || null;
  $('csv').value = st.csv || ''; if (st.model) $('model').value = st.model; if (st.tau2) $('tau2').value = st.tau2; $('kh').checked = st.kh !== false;
  S.flow = st.flow || S.flow; S.fhigh = st.fhigh || S.fhigh; $('flow').value = st.flow || ''; $('fhigh').value = st.fhigh || '';
  if (S.questions.length) renderQuestions({ source: 'ai', questions: S.questions });
  if (S.chosen || S.questionText) { setStepEnabled(2, true); setStepEnabled(3, true); setStepEnabled(4, true); markDone(1); prepareProtocolStep(); prepareDataStep(); }
  else { setStepEnabled(3, true); setStepEnabled(4, true); prepareDataStep(); }
  if (S.protocol) renderProtocol({ source: 'ai', protocol: S.protocol });
  prepareSearchStep();
  if (st.searchMeta) { S.searchMeta = st.searchMeta; renderSearchMeta(st.searchMeta); }
  if (st.searchRecords && st.searchRecords.length) { S.searchRecords = st.searchRecords; $('screenCard').style.display = ''; renderResults(); }
  if (st.searchQ) $('searchQ').value = st.searchQ;
  if (st.prisma) Object.entries(st.prisma).forEach(([k, v]) => { const el = $('pf_' + k); if (el) el.value = v; });
  if (st.result) {
    S.result = st.result; S.prismaSvg = st.prismaSvg || null; S.robSvg = st.robSvg || null; S.grade = st.grade || null;
    renderSynthesis(st.result); renderDiagnostics(st.result);
    setStepEnabled(5, true); setStepEnabled(6, true); setStepEnabled(7, true); setStepEnabled(8, true); markDone(4);
    $('noResult').style.display = 'none'; $('articleWrap').style.display = '';
    await prepareQualityStep();
    if (st.robTool) { $('robTool').value = st.robTool; buildRobGrid(); }
    if (st.robRatings) restoreRobRatings(st.robRatings);
    if (S.prismaSvg) { $('prismaPlot').innerHTML = S.prismaSvg; $('prismaPlot').style.display = ''; $('prismaDl').style.display = ''; }
    if (S.robSvg) { $('robPlot').innerHTML = S.robSvg; $('robPlot').style.display = ''; $('robDl').style.display = ''; }
    if (S.grade) { if (S.grade.design) $('gradeDesign').value = S.grade.design; renderGrade(S.grade); }
  }
  if (st.facts) $('facts').textContent = st.facts;
  if (st.manuscript && Object.keys(st.manuscript).length) { S.manuscript = st.manuscript; renderSections(); if (S.ai) $('aiAllBtn').style.display = ''; }
  goStep(st.step || 1);
}

init();
refreshProjects();

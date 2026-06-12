const $ = (id) => document.getElementById(id);
let last = null;

const fmt = (x, dp = 2) => (x === null || x === undefined || Number.isNaN(x)) ? '—' : Number(x).toFixed(dp);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function downloadText(name, text, type) {
  const blob = new Blob([text], { type: type || 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- Examples & templates ----
async function loadExamples() {
  try {
    const ex = await (await fetch('/examples')).json();
    const sel = $('exampleSel');
    Object.entries(ex).forEach(([k, v]) => {
      const o = document.createElement('option');
      o.value = k; o.textContent = v.title;
      sel.appendChild(o);
    });
  } catch (e) { /* offline-friendly */ }

  try {
    const t = (await (await fetch('/templates')).json()).templates;
    const box = $('templates');
    t.forEach((kind) => {
      const b = document.createElement('button');
      b.textContent = kind;
      b.onclick = () => window.location = `/templates/${kind}`;
      box.appendChild(b);
    });
  } catch (e) { /* ignore */ }
}

$('exampleSel').onchange = async (e) => {
  const key = e.target.value;
  if (!key) return;
  const data = await (await fetch('/examples/' + key)).json();
  $('csv').value = data.csv.trim();
  if (data.favours_low) $('flow').value = data.favours_low;
  if (data.favours_high) $('fhigh').value = data.favours_high;
};
$('clear').onclick = () => { $('csv').value = ''; };

// ---- Tabs ----
$('tabs').addEventListener('click', (e) => {
  const tab = e.target.dataset.tab;
  if (!tab) return;
  document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach((p) => p.classList.toggle('active', p.id === 'panel-' + tab));
});

// ---- Run ----
$('run').onclick = async () => {
  $('err').textContent = '';
  const body = {
    csv: $('csv').value,
    model: $('model').value,
    tau2_method: $('tau2').value,
    knapp_hartung: $('kh').checked,
    favours_low: $('flow').value,
    favours_high: $('fhigh').value,
  };
  $('run').disabled = true;
  $('run').textContent = 'Calculando…';
  try {
    const r = await fetch('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Error en el análisis');
    last = data;
    render(data);
    $('welcome').style.display = 'none';
    $('results').style.display = '';
  } catch (e) {
    $('err').textContent = e.message;
  } finally {
    $('run').disabled = false;
    $('run').textContent = '▶ Ejecutar meta-análisis';
  }
};

function stat(k, v, big) {
  return `<div class="stat ${big ? 'big' : ''}"><div class="k">${k}</div><div class="v">${v}</div></div>`;
}

function interpret(d) {
  const p = d.pooled, m = d.measure;
  const ratio = d.log_scale;
  const sig = (ratio ? (p.ci_low > 1 || p.ci_high < 1) : (p.ci_low > 0 || p.ci_high < 0));
  const dir = ratio
    ? (p.estimate < 1 ? 'una reducción' : 'un aumento')
    : (p.estimate < 0 ? 'un efecto a favor de la izquierda' : 'un efecto a favor de la derecha');
  const het = d.heterogeneity.i2 >= 75 ? 'considerable' : d.heterogeneity.i2 >= 50 ? 'sustancial' : d.heterogeneity.i2 >= 30 ? 'moderada' : 'baja';
  let s = `El ${d.measure_label.toLowerCase()} combinado es <b>${fmt(p.estimate)}</b> (IC 95% ${fmt(p.ci_low)}–${fmt(p.ci_high)}, p=${fmt(p.p_value, 3)}), `;
  s += sig ? `indicando ${dir} estadísticamente significativa. ` : `sin diferencia estadísticamente significativa. `;
  s += `La heterogeneidad entre estudios es <b>${het}</b> (I²=${fmt(d.heterogeneity.i2, 0)}%).`;
  if (p.pi_low != null) s += ` El intervalo de predicción 95% (${fmt(p.pi_low)}–${fmt(p.pi_high)}) describe el rango esperado para un estudio futuro.`;
  return s;
}

function render(d) {
  const p = d.pooled, h = d.heterogeneity, m = d.measure;

  // SUMMARY
  $('stats').innerHTML = [
    stat(`${m} combinado`, `${fmt(p.estimate)} [${fmt(p.ci_low)}, ${fmt(p.ci_high)}]`, true),
    stat('Estudios (k)', d.k),
    stat('p-valor', fmt(p.p_value, 4)),
    stat('I²', fmt(h.i2, 0) + '%'),
    stat('τ²', fmt(h.tau2, 3)),
    p.pi_low != null ? stat('Predicción 95%', `[${fmt(p.pi_low)}, ${fmt(p.pi_high)}]`) : '',
  ].join('');
  $('interp').innerHTML = interpret(d);
  const model = d.model === 'random' ? `efectos aleatorios (${d.tau2_method}${d.knapp_hartung ? ', Knapp-Hartung' : ''})` : 'efecto fijo';
  $('hetero').innerHTML = `Modelo: ${model}. Heterogeneidad: Q=${fmt(h.q)} (gl=${h.q_df}, p=${fmt(h.q_p, 3)}), I²=${fmt(h.i2, 0)}%, τ²=${fmt(h.tau2, 4)}, H²=${fmt(h.h2)}.`;
  $('warnings').innerHTML = (d.warnings && d.warnings.length)
    ? `<div class="note"><b>Avisos:</b> ${d.warnings.map(esc).join(' · ')}</div>` : '';
  $('forest').innerHTML = d.forest_svg;

  // SENSITIVITY
  if (d.loo_forest_svg) {
    $('loo').innerHTML = d.loo_forest_svg;
  } else {
    $('loo').innerHTML = '<div class="empty">Se necesitan ≥3 estudios para el análisis leave-one-out.</div>';
  }
  if (d.cumulative && d.cumulative.length) {
    const hasYears = $('csv').value.toLowerCase().includes('year');
    $('cumNote').textContent = hasYears
      ? 'Estudios añadidos en orden cronológico (columna year).'
      : 'Sin columna year: se usa el orden de entrada. Añade year para orden cronológico.';
    const rows = d.cumulative.map((c) =>
      `<tr><td>${esc(c.added)}</td><td>${c.k}</td><td>${fmt(c.estimate)} [${fmt(c.ci_low)}, ${fmt(c.ci_high)}]</td><td>${fmt(c.i2, 0)}%</td><td>${fmt(c.p_value, 3)}</td></tr>`).join('');
    $('cumTable').innerHTML = `<tr><th>+ Estudio</th><th>k</th><th>${m} acumulado [IC95%]</th><th>I²</th><th>p</th></tr>${rows}`;
  } else {
    $('cumTable').innerHTML = '';
    $('cumNote').textContent = 'Se necesitan ≥2 estudios.';
  }

  // SUBGROUPS
  if (d.subgroups) {
    const s = d.subgroups;
    const rows = s.groups.map((g) =>
      `<tr><td>${esc(g.subgroup)}</td><td>${g.k}</td><td>${fmt(g.estimate)} [${fmt(g.ci_low)}, ${fmt(g.ci_high)}]</td><td>${fmt(g.i2, 0)}%</td></tr>`).join('');
    const sigTxt = s.p_value < 0.05
      ? `<b>Hay diferencia significativa</b> entre subgrupos (p=${fmt(s.p_value, 3)}).`
      : `No hay evidencia de diferencia entre subgrupos (p=${fmt(s.p_value, 3)}).`;
    $('subCard').innerHTML = `<h2>Análisis de subgrupos</h2>
      <div style="overflow-x:auto"><table><tr><th>Subgrupo</th><th>k</th><th>${m} [IC95%]</th><th>I²</th></tr>${rows}</table></div>
      <div class="interp" style="margin-top:14px">Prueba entre subgrupos: Q=${fmt(s.q_between)} (gl=${s.df}). ${sigTxt}</div>`;
  } else {
    $('subCard').innerHTML = `<h2>Análisis de subgrupos</h2>
      <div class="empty">Añade una columna <code>subgroup</code> a tu CSV (con ≥2 valores distintos) para comparar subgrupos.</div>`;
  }

  // BIAS
  $('funnel').innerHTML = d.funnel_svg;
  $('baujat').innerHTML = d.baujat_svg || '<div class="empty">≥3 estudios para Baujat.</div>';
  if (d.egger) {
    $('egger').innerHTML = `<b>Prueba de Egger</b> (asimetría del funnel / efectos de estudios pequeños): intercepto=${fmt(d.egger.intercept)}, p=${fmt(d.egger.p_value, 3)}.
      ${d.egger.p_value < 0.05 ? '<span style="color:var(--warn)">Asimetría significativa: posible sesgo de publicación.</span>' : 'Sin evidencia fuerte de asimetría.'}
      ${d.egger.note ? '<br><span class="muted">' + esc(d.egger.note) + '</span>' : ''}`;
  } else {
    $('egger').innerHTML = '<span class="muted">Prueba de Egger: se necesitan ≥3 estudios.</span>';
  }
  if (d.trim_fill) {
    const t = d.trim_fill;
    $('trimfill').innerHTML = t.k0 > 0
      ? `<b>Trim-and-fill (Duval & Tweedie):</b> se estiman <b>${t.k0}</b> estudio(s) faltante(s) en el lado <b>${t.side === 'left' ? 'izquierdo' : 'derecho'}</b>.
         Estimación observada ${fmt(t.observed_estimate)} → ajustada <b>${fmt(t.adjusted_estimate)}</b> [${fmt(t.adjusted_ci_low)}, ${fmt(t.adjusted_ci_high)}].
         Los estudios imputados aparecen como círculos rojos en el funnel.`
      : `<b>Trim-and-fill:</b> no se estiman estudios faltantes (k0=0). El funnel es simétrico según este método.`;
  } else {
    $('trimfill').innerHTML = '<span class="muted">Trim-and-fill: se necesitan ≥3 estudios.</span>';
  }

  // DATA
  const rows = d.studies.map((s) =>
    `<tr><td>${esc(s.label)}</td>${d.subgroups ? `<td>${esc(s.subgroup || '—')}</td>` : ''}<td>${fmt(s.estimate)}</td><td>[${fmt(s.ci_low)}, ${fmt(s.ci_high)}]</td><td>${fmt(s.weight_pct, 1)}%</td><td class="muted">${esc(s.note || '')}</td></tr>`).join('');
  $('studies').innerHTML = `<tr><th>Estudio</th>${d.subgroups ? '<th>Subgrupo</th>' : ''}<th>${m}</th><th>IC 95%</th><th>Peso</th><th>Nota</th></tr>${rows}`;
}

// ---- Downloads ----
$('dlForest').onclick = () => last && downloadText('forest.svg', last.forest_svg, 'image/svg+xml');
$('dlFunnel').onclick = () => last && downloadText('funnel.svg', last.funnel_svg, 'image/svg+xml');
$('dlCsv').onclick = () => {
  if (!last) return;
  const header = 'study_label,subgroup,estimate,ci_low,ci_high,weight_pct,yi,se\n';
  const lines = last.studies.map((s) => `"${s.label}",${s.subgroup || ''},${s.estimate},${s.ci_low},${s.ci_high},${s.weight_pct},${s.yi},${s.se}`).join('\n');
  downloadText('metaforge_estimates.csv', header + lines, 'text/csv');
};

loadExamples();

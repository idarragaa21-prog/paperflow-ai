const $ = (id) => document.getElementById(id);

const EXAMPLE = `study_label,year,effect_measure,outcome_type,a_events,b_non_events,c_events,d_non_events
Granger 2011 (ARISTOTLE),2011,OR,binary,212,8908,265,8795
Patel 2011 (ROCKET-AF),2011,OR,binary,269,6989,306,6985
Connolly 2009 (RE-LY),2009,OR,binary,134,5973,199,5823
Giugliano 2013 (ENGAGE),2013,OR,binary,296,6739,337,6695`;

let last = null;

function fmt(x, dp = 2) { return (x === null || x === undefined) ? '—' : Number(x).toFixed(dp); }

function downloadText(name, text, type) {
  const blob = new Blob([text], { type: type || 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

$('example').onclick = () => { $('csv').value = EXAMPLE; };
$('clear').onclick = () => { $('csv').value = ''; };

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
  $('run').textContent = 'Running…';
  try {
    const r = await fetch('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Analysis failed');
    last = data;
    render(data);
  } catch (e) {
    $('err').textContent = e.message;
  } finally {
    $('run').disabled = false;
    $('run').textContent = 'Run meta-analysis';
  }
};

function render(d) {
  const p = d.pooled, h = d.heterogeneity;
  const measure = d.measure;
  $('resultCard').style.display = '';
  $('stats').innerHTML = [
    stat('Pooled ' + measure, `${fmt(p.estimate)} [${fmt(p.ci_low)}, ${fmt(p.ci_high)}]`, true),
    stat('Studies (k)', d.k),
    stat('p-value', fmt(p.p_value, 4)),
    stat('I²', fmt(h.i2, 0) + '%'),
    stat('τ²', fmt(h.tau2, 3)),
    p.pi_low != null ? stat('95% prediction interval', `[${fmt(p.pi_low)}, ${fmt(p.pi_high)}]`) : '',
  ].join('');
  const model = d.model === 'random' ? `random-effects (${d.tau2_method}${d.knapp_hartung ? ', Knapp-Hartung' : ''})` : 'fixed-effect';
  $('hetero').textContent = `Model: ${model}. Heterogeneity: Q=${fmt(h.q)} (df=${h.q_df}, p=${fmt(h.q_p, 3)}), I²=${fmt(h.i2, 0)}%, τ²=${fmt(h.tau2, 4)}, H²=${fmt(h.h2)}.`;
  if (d.egger) {
    $('egger').textContent = `Egger's test for small-study effects: intercept=${fmt(d.egger.intercept, 2)}, p=${fmt(d.egger.p_value, 3)}${d.egger.note ? ' — ' + d.egger.note : ''}.`;
  } else {
    $('egger').textContent = '';
  }

  $('forestCard').style.display = '';
  $('forest').innerHTML = d.forest_svg;
  $('funnelCard').style.display = '';
  $('funnel').innerHTML = d.funnel_svg;

  $('tableCard').style.display = '';
  const rows = d.studies.map((s) =>
    `<tr><td>${escapeHtml(s.label)}</td><td>${fmt(s.estimate)}</td><td>[${fmt(s.ci_low)}, ${fmt(s.ci_high)}]</td><td>${fmt(s.weight_pct, 1)}%</td><td class="muted">${escapeHtml(s.note || '')}</td></tr>`
  ).join('');
  $('studies').innerHTML = `<tr><th>Study</th><th>${measure}</th><th>95% CI</th><th>Weight</th><th>Note</th></tr>${rows}`;
}

function stat(k, v, big) {
  return `<div class="stat ${big ? 'big' : ''}"><div class="k">${k}</div><div class="v">${v}</div></div>`;
}
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

$('dlForest').onclick = () => last && downloadText('forest.svg', last.forest_svg, 'image/svg+xml');
$('dlFunnel').onclick = () => last && downloadText('funnel.svg', last.funnel_svg, 'image/svg+xml');
$('dlCsv').onclick = () => {
  if (!last) return;
  const header = 'study_label,estimate,ci_low,ci_high,weight_pct,yi,se\n';
  const lines = last.studies.map((s) => `"${s.label}",${s.estimate},${s.ci_low},${s.ci_high},${s.weight_pct},${s.yi},${s.se}`).join('\n');
  downloadText('study_estimates.csv', header + lines, 'text/csv');
};

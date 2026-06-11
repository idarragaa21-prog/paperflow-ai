<div align="center">

# MetaForge

**A local-first meta-analysis tool for epidemiologists.**

Paste the data you already have — 2×2 tables, arm summaries, or effect + CI —
and get a random/fixed-effects synthesis with a publication-style forest plot.
No cloud, no account, no LLM. Your data never leaves your machine.

</div>

---

## Why

Most meta-analysis software is either a heavyweight desktop app (RevMan), an R
package that assumes you write R (`metafor`), or a paid web service that wants
your data in the cloud. MetaForge is a single small service you run
locally: open a page, paste a CSV, read your pooled estimate and forest plot.

It implements the statistics an expert actually expects:

- Effect sizes from **2×2 count tables** (OR / RR / RD) with a Haldane-Anscombe
  continuity correction, from **arm summaries** (mean difference, Hedges' *g*
  SMD with small-sample correction), or from a **precomputed effect + SE/CI**.
- **Fixed-effect** and **random-effects** pooling with **REML**, **Paule-Mandel**
  or **DerSimonian-Laird** τ².
- **Knapp-Hartung** variance adjustment (t-based CIs) for random-effects models.
- **Higgins prediction interval**, I², τ², H², Cochran's Q.
- **Egger's test** for small-study effects and a **funnel plot**.

## Quick start

```bash
git clone <your-repo-url> metaforge
cd metaforge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn metaforge.api:app --reload --port 8000
```

Open **http://127.0.0.1:8000**, click *Load example*, and hit *Run*.

## Input format

A CSV with a header row. One row per study (or per effect). Required: a
`study_label`. Then provide **one** of:

| Data you have | Columns |
|---|---|
| Binary 2×2 table | `effect_measure` (OR/RR/RD), `a_events`, `b_non_events`, `c_events`, `d_non_events` |
| Continuous arms | `effect_measure` (MD/SMD), `n_intervention`, `mean_intervention`, `sd_intervention`, `n_control`, `mean_control`, `sd_control` |
| Precomputed effect | `effect_measure`, `effect_value`, and either `effect_se` or `ci_lower_95` + `ci_upper_95` |
| Generic inverse-variance | `yi`, `se` (already on the analysis scale) |

`a`/`b` are the intervention arm's events / non-events; `c`/`d` the control arm's.

### Example

```csv
study_label,effect_measure,a_events,b_non_events,c_events,d_non_events
ARISTOTLE,OR,212,8908,265,8795
ROCKET-AF,OR,269,6989,306,6985
RE-LY,OR,134,5973,199,5823
ENGAGE,OR,296,6739,337,6695
```

→ pooled OR ≈ 0.81 [0.72, 0.91], I² ≈ 43%, with forest and funnel plots.

## API

`POST /analyze` with `{"csv": "...", "model": "random", "tau2_method": "REML",
"knapp_hartung": true}` (or `{"rows": [...]}`) returns the pooled estimate,
heterogeneity, Egger's test, per-study weights, and forest/funnel SVGs.

Use it as a library too:

```python
from metaforge import analyze_csv
out = analyze_csv(open("data.csv").read(), model="random", tau2_method="REML")
print(out["pooled"]["estimate"], out["heterogeneity"]["i2"])
```

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

## Scope & honesty

This covers **univariate pairwise** meta-analysis well. It does **not** (yet) do
network meta-analysis, dose-response, multilevel/multivariate models, or
diagnostic-test accuracy. For those, reach for `metafor`/`netmeta`. GRADE and
PRISMA tracking are out of scope by design — this tool does one thing.

## License

MIT — see [LICENSE](LICENSE).

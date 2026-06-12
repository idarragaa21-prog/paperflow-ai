<div align="center">

# ⬡ MetaForge

**Local-first pairwise meta-analysis for epidemiologists.**

Paste the data you already have — 2×2 tables, person-time, arm summaries,
proportions, correlations, or effect + CI — and get a random/fixed-effects
synthesis with forest and funnel plots, sensitivity analyses, subgroup tests
and publication-bias diagnostics. No cloud, no account, no LLM.
Your data never leaves your machine.

</div>

---

## Why

Most meta-analysis software is either a heavyweight desktop app (RevMan), an R
package that assumes you write R (`metafor`), or a paid web service that wants
your data in the cloud. MetaForge is one small program you run locally: open a
page, paste a CSV, read your pooled estimate, forest plot and diagnostics — or
drive the same engine from the command line or a REST API.

## What it does

**Effect sizes** from whatever you have:

| Data | Measure | Columns |
|---|---|---|
| Binary 2×2 | OR / RR / RD | `a_events, b_non_events, c_events, d_non_events` |
| Person-time | IRR | `events_intervention, time_intervention, events_control, time_control` |
| Continuous arms | MD / SMD (Hedges' *g*) | `n_/mean_/sd_intervention`, `n_/mean_/sd_control` |
| Single-group proportion | PLOGIT | `events, n_total` |
| Correlation | ZCOR (Fisher z) | `r, n_total` |
| Precomputed | any | `effect_value` + (`effect_se` or `ci_lower_95`+`ci_upper_95`) |
| Generic | any | `yi, se` (already on the analysis scale) |

**Synthesis**: fixed-effect and random-effects pooling with **REML**,
**Paule-Mandel** or **DerSimonian-Laird** τ²; **Knapp-Hartung** adjustment;
**Higgins prediction interval**; I², τ², H², Cochran's Q.

**Diagnostics a referee will ask for**:
- **Leave-one-out** and **cumulative** meta-analysis
- **Subgroup analysis** with a between-group test (add a `subgroup` column)
- **Egger's test** + **funnel plot**
- **Trim-and-fill** (Duval & Tweedie) with imputed studies on the funnel
- **Baujat** influence plot

Everything has a **forest/funnel/leave-one-out/Baujat SVG** you can download for
your manuscript.

## Quick start

```bash
git clone <your-repo-url> metaforge
cd metaforge
./run.sh                 # creates a venv, installs deps, starts the server
```

Open **http://127.0.0.1:8000**, pick an example from the dropdown, hit *Run*.

<details>
<summary>Manual / make / docker</summary>

```bash
# manual
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn metaforge.api:app --port 8000

# make
make install && make run

# docker
docker compose up --build      # serves on http://127.0.0.1:8000
```
</details>

## Command line

No server needed:

```bash
python -m metaforge examples/doac_or.csv                 # text summary
python -m metaforge examples/doac_or.csv --out results/  # + SVGs, estimates.csv, results.json
python -m metaforge data.csv --model fixed --tau2 DL --no-kh --json
```

```
MetaForge — Odds ratio (OR), k=4 studies
Model: random, REML, Knapp-Hartung

  Pooled OR: 0.808  (95% CI 0.660 to 0.988)
  p-value:   0.043
  95% PI:    0.535 to 1.220
  Heterogeneity: I²=43%  τ²=0.006  Q=5.239 (df=3, p=0.155)
  Egger's test:  intercept=-9.444, p=0.013
  Subgroups:     Q_between=4.367 (df=1, p=0.037)
```

## Library

```python
from metaforge import analyze_csv
out = analyze_csv(open("data.csv").read(), model="random", tau2_method="REML")
print(out["pooled"]["estimate"], out["heterogeneity"]["i2"])
print(out["subgroups"], out["trim_fill"])     # diagnostics
open("forest.svg", "w").write(out["forest_svg"])
```

## REST API

`POST /analyze` with `{"csv": "...", "model": "random", "tau2_method": "REML",
"knapp_hartung": true}` (or `{"rows": [...]}`). Other endpoints: `GET /examples`,
`GET /examples/{key}`, `GET /templates`, `GET /templates/{kind}`, `GET /health`.
Interactive docs at `/docs`.

## Input format

A CSV with a header row, one row per study. Required: `study_label`,
`effect_measure`. Optional: `year` (enables chronological cumulative MA),
`subgroup` (enables subgroup comparison). All studies in one file must share the
same `effect_measure`. See `examples/` for ready-to-run datasets and blank
templates, or download templates from the UI.

```csv
study_label,year,subgroup,effect_measure,a_events,b_non_events,c_events,d_non_events
Connolly 2009 (RE-LY),2009,Thrombin inhibitor,OR,134,5973,199,5823
Granger 2011 (ARISTOTLE),2011,Factor Xa,OR,212,8908,265,8795
Patel 2011 (ROCKET-AF),2011,Factor Xa,OR,269,6989,306,6985
Giugliano 2013 (ENGAGE),2013,Factor Xa,OR,296,6739,337,6695
```

## Tests

```bash
pip install -r requirements.txt
pytest -q          # 44 tests, statistics validated against known values
```

## Scope & honesty

MetaForge does **univariate pairwise** meta-analysis thoroughly. It does **not**
do network meta-analysis, dose-response, multivariate/multilevel models, or
diagnostic-test accuracy — for those, reach for `metafor`/`netmeta`. GRADE and
PRISMA tracking are out of scope by design: this tool does one job well.

The statistics follow standard references (DerSimonian & Laird 1986; Knapp &
Hartung 2003; Higgins et al. 2009; Duval & Tweedie 2000; Viechtbauer 2005).
Validate against your software of record before publishing.

## License

MIT — see [LICENSE](LICENSE).

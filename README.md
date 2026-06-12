<div align="center">

# ⬡ MetaForge

**A local-first research workspace for epidemiologists — from a topic to a manuscript.**

Type any topic, in any language, and MetaForge walks you through the whole
study: it proposes sharp research questions, drafts a review protocol (criteria
+ PubMed search), runs the meta-analysis with publication-style plots, checks
sensitivity and publication bias, and drafts the manuscript from your real
numbers. No cloud, no API key, no data leaving your machine.

</div>

---

## The pipeline

```
1. Question   →  2. Protocol  →  3. Data  →  4. Synthesis  →  5. Diagnostics  →  6. Manuscript
   (AI)            (AI)            CSV          meta-analysis    sensitivity/bias    (AI, grounded)
```

1. **Question** — type a topic in any language; get specific, developable
   research questions, each with its framework (PICO/PECO/SPIDER), study design,
   FINER feasibility note and the effect measure to synthesise.
2. **Protocol** — for the chosen question: objective, inclusion/exclusion
   criteria, eligible designs, a ready-to-paste **PubMed search string**, and the
   exact data-extraction columns.
3. **Data** — paste a CSV (or load an example / download a template). One row per
   study; MetaForge computes the effect sizes for you.
4. **Synthesis** — fixed/random-effects pooling (REML, Paule-Mandel or DL),
   Knapp-Hartung, prediction interval, I²/τ²/Q, plain-language interpretation and
   a forest plot.
5. **Diagnostics** — leave-one-out, cumulative MA, subgroup test, Egger's test,
   trim-and-fill and a Baujat influence plot.
6. **Manuscript** — drafts Title, Abstract, Methods, **Results (with your exact
   numbers)**, Discussion, Limitations and Conclusion. Improve any section with
   AI, edit inline, export Markdown.

## AI, with no API key

When MetaForge needs AI (questions, protocol, manuscript) it calls the **`claude`
CLI you already log in with** (`claude login`) — using your existing Claude
subscription, not a separate API key, not pay-per-use. If the CLI isn't
available, every AI step **falls back to a deterministic local generator**, so
the app always works offline (the Results paragraph is still written from your
real data).

Check status in the app (the "IA activa / Modo local" pill) or via `GET /ai-status`.

## Quick start

```bash
git clone <your-repo-url> metaforge   # or: git clone metaforge.bundle metaforge
cd metaforge
./run.sh                               # venv + deps + server
# (optional, for AI features) make sure you've run `claude login` once
```

Open **http://127.0.0.1:8000** and start at step 1.

<details><summary>Manual / make / docker</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn metaforge.api:app --port 8000
# or
make install && make run
# or
docker compose up --build
```
</details>

## Effect measures (step 3)

| Data you have | `effect_measure` | Columns |
|---|---|---|
| Binary 2×2 | OR / RR / RD | `a_events, b_non_events, c_events, d_non_events` |
| Person-time | IRR | `events_intervention, time_intervention, events_control, time_control` |
| Continuous arms | MD / SMD | `n_/mean_/sd_intervention`, `n_/mean_/sd_control` |
| Proportion / prevalence | PLOGIT | `events, n_total` |
| Correlation | ZCOR | `r, n_total` |
| Precomputed | any | `effect_value` + (`effect_se` or `ci_lower_95`+`ci_upper_95`) |
| Generic | any | `yi, se` |

Always include `study_label` and `effect_measure`. Optional: `year` (enables
cumulative MA), `subgroup` (enables the subgroup test). All rows share one
measure. See `examples/` for ready-to-run datasets and blank templates.

## Command line & library

```bash
python -m metaforge examples/doac_or.csv --out results/   # analysis + SVGs + CSV + JSON
```

```python
from metaforge import analyze_csv, generate_questions, generate_protocol, generate_manuscript
out = analyze_csv(open("data.csv").read(), model="random", tau2_method="REML")
draft = generate_manuscript("¿X reduce Y?", out, mode="local")   # grounded on real numbers
print(draft["sections"]["results"])
```

## REST API

`/questions`, `/protocol`, `/manuscript`, `/manuscript/section`, `/analyze`,
`/examples`, `/templates`, `/ai-status`, `/health`. Interactive docs at `/docs`.

## Tests

```bash
pip install -r requirements.txt
pytest -q          # 66 tests; statistics validated against known values
```

## Scope & honesty

MetaForge does **univariate pairwise** meta-analysis thoroughly, plus question /
protocol / manuscript assistance. It does **not** do network meta-analysis,
dose-response, multilevel models or diagnostic-test accuracy — use
`metafor`/`netmeta` for those. The AI assists drafting; **you remain the author**
— review every AI-written sentence and validate the statistics against your
software of record before publishing.

Statistics follow standard references (DerSimonian & Laird 1986; Knapp & Hartung
2003; Higgins et al. 2009; Duval & Tweedie 2000; Viechtbauer 2005).

## License

MIT — see [LICENSE](LICENSE).

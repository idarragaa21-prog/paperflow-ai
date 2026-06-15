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
1.Question → 2.Protocol → 3.Search → 4.Data → 5.Synthesis → 6.Diagnostics → 7.Quality → 8.Manuscript
  (AI)        (AI)         real DB     CSV      meta-analysis  sensitivity     PRISMA+RoB   (AI, grounded)
                          +AI screen                                          +GRADE
```

1. **Question** — type a topic in any language; get specific, developable
   research questions, each with its framework (PICO/PECO/SPIDER), study design,
   FINER feasibility note and the effect measure to synthesise.
2. **Protocol** — for the chosen question: objective, inclusion/exclusion
   criteria, eligible designs, a ready-to-paste **PubMed search string**, and the
   exact data-extraction columns.
3. **Search & screening** — actually queries **Europe PMC** and/or **PubMed**
   (native MeSH via E-utilities), **deduplicates** across sources, and retrieves
   real records with abstracts and open-access links. **AI-screens each title/
   abstract against your protocol's inclusion/exclusion criteria** (include /
   exclude / maybe + reason); an optional **dual-reviewer mode** runs two
   independent AI passes and reports **Cohen's κ** with conflicts flagged.
   First-pass only — you verify every decision (PRISMA/Cochrane), with an optional
   **full-text screening** second phase. For included open-access studies, **AI
   extracts the effect data from the full text — parsing the tables, not just the
   narrative** (2×2, means/SDs or effect+CI) with the supporting quote. For a full
   data sheet, **«Extraer TODO a Excel»** reads every table, the text and the figure
   captions of each open-access article and fills a three-sheet workbook
   (study characteristics · every reported outcome · a ready-for-meta-analysis
   sheet) — fanning each article out into small parallel AI calls so it captures
   *everything* without timing out. Nothing is invented: blank means not reported.
   Counts flow into the PRISMA diagram. **Zotero integration**: import RIS/BibTeX
   to screen references you already have, and export included studies to RIS,
   BibTeX or straight to your **Zotero library** — via the Web API, or the local desktop connector with **no API key** (just have Zotero open).
4. **Data** — paste a CSV (or load an example / download a template). One row per
   study; MetaForge computes the effect sizes for you.
5. **Synthesis** — fixed/random-effects pooling (REML, Paule-Mandel or DL),
   Knapp-Hartung, prediction interval, I²/τ²/Q, plain-language interpretation and
   a forest plot.
6. **Diagnostics** — leave-one-out, cumulative MA, subgroup test, Egger's test,
   trim-and-fill, a Baujat influence plot, and **meta-regression** (moderator
   analysis with a bubble plot, residual τ² and R²).
7. **Quality & figures** — a **PRISMA 2020 flow diagram** (single- or two-column with "other methods"), a **risk-of-bias**
   traffic-light plot (RoB 2 / ROBINS-I), and a **GRADE** certainty assessment
   (auto-suggested downgrades + manual override). All download as SVG.
8. **Manuscript** — drafts Title, Abstract, Methods, **Results (with your exact
   numbers)**, Discussion, Limitations and Conclusion. Improve any section with
   AI, edit inline, **save/resume the whole review as a project**, and export
   **Markdown, Word (.docx with embedded figures + GRADE table) or PDF**.

## AI, with no API key

When MetaForge needs AI (questions, protocol, manuscript) it calls the **`claude`
CLI you already log in with** (`claude login`) — using your existing Claude
subscription, not a separate API key, not pay-per-use. If the CLI isn't
available, every AI step **falls back to a deterministic local generator**, so
the app always works offline (the Results paragraph is still written from your
real data).

Check status in the app (the "IA activa / Modo local" pill) or via `GET /ai-status`.

## Quick start (macOS / Linux)

```bash
git clone metaforge.bundle metaforge   # or your repo URL
cd metaforge
./run.sh
```

`run.sh` creates a virtual environment, installs the (lean, wheels-only)
dependencies, starts the server and **opens your browser** at
**http://127.0.0.1:8000**. First launch takes ~20 s to install; afterwards it
starts instantly. No system libraries needed.

- **AI features** (questions, protocol, screening, extraction, manuscript) use
  the `claude` CLI — run `claude login` once. Without it, the app still runs in
  local mode.
- **Sharper figures inside the Word export** are optional: `pip install cairosvg`
  (needs `brew install cairo`). The default `svglib` renderer needs nothing.

If a previous attempt left a broken environment: `rm -rf .venv && ./run.sh`.

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

`/questions`, `/protocol`, `/search`, `/screen`, `/analyze`, `/manuscript`,
`/manuscript/section`, `/manuscript/docx`, `/prisma`, `/rob`, `/rob/tools`,
`/extract`, `/extract/full`, `/extract/excel`, `/screen/fulltext`, `/meta-regression`, `/citations/export`, `/citations/import`, `/zotero/push`, `/grade`, `/projects`(+`/{id}`), `/examples`, `/templates`, `/ai-status`,
`/health`. Interactive docs at `/docs`.

## Tests

```bash
pip install -r requirements.txt
pytest -q          # 121 tests; statistics validated against known values
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

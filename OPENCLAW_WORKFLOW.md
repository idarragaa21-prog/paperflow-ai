# OpenClaw 2026 Workflow v1

## What this is

This repo now contains a general-purpose AI orchestrator scaffold, not a papers-only pipeline.

`OpenClaw` is the director.
It receives a task, routes it to the right specialist, stores state on disk, and returns artifacts plus logs.

The current v1 supports five general agents:

- `research-scout` for web research, source discovery, article triage, and evidence gathering.
- `document-miner` for PDF and spreadsheet validation, landing-page fallback, and structured extraction scaffolds.
- `coder-builder` for repo inspection, relevant file discovery, validation planning, and coding-oriented task prep.
- `ops-runner` for operational shell tasks, local setup, installations, and Mac/system execution through safe commands.
- `voice-agent` for local text-to-speech and local audio transcription.

## Mental model

Think of this as a personal operating layer for mixed AI work:

- research and browsing
- PDFs and spreadsheets
- coding and repo work
- shell and Mac operations
- voice and audio workflows
- long-running tasks with persistent state

Papers are only one use case.
The same runtime is meant to support daily technical work in general.

## Runtime shape

Every task lands in:

- `.orchestrator-runtime/tasks/<task_id>/task.json`
- `.orchestrator-runtime/tasks/<task_id>/plan.json`
- `.orchestrator-runtime/tasks/<task_id>/events.jsonl`
- `.orchestrator-runtime/tasks/<task_id>/artifacts/`
- `.orchestrator-runtime/tasks/<task_id>/outputs/`

That gives you a durable trail of:

- what the user asked
- how OpenClaw routed it
- which agent ran
- what files/results were produced
- what warnings/fallbacks happened

## Agent selection

The router currently prioritizes:

- explicit `voice`/audio inputs -> `voice-agent`
- explicit shell/command/system inputs -> `ops-runner`
- explicit repo/coding inputs -> `coder-builder`
- systematic review / article workflows -> `research-scout` + `document-miner`
- fallback general research -> `research-scout`

## Example task types

### 1. General web research

```bash
python3 -m orchestrator.cli run --task examples/task.web-research.json
```

Use when you want:
- topic exploration
- source discovery
- candidate links and identifiers
- first-pass evidence gathering

### 2. Systematic review / evidence workflow

```bash
./.orchestrator-venv/bin/python -m orchestrator.cli run --task examples/task.review-systematic.json
```

Use when you want:
- candidate article discovery
- landing-page/PDF validation
- structured evidence table output

Batch article + workbook fill:

```bash
./.orchestrator-venv/bin/python -m orchestrator.cli run --task examples/task.article-excel.json
```

This path can:
- accept article URLs, DOIs, local PDFs, or simple titles
- download or validate PDFs
- extract basic study fields
- write a filled `.xlsx` workbook into the task runtime

### 3. Coding / repo investigation

```bash
python3 -m orchestrator.cli run --task examples/task.coding.json
```

Current outputs include:
- `artifacts/repo_snapshot.json`
- `artifacts/patch_plan.json`
- `outputs/patch_outline.md`
- `outputs/test_report.json`
- `outputs/edit_report.json` when scoped edits are requested

Fast launch mode for chat-driven work:

```bash
python3 -m orchestrator.cli launch \
  --mode coding \
  --repo-path "/Users/diegoalejandroidarragalopez/Documents/New project" \
  --objective "prepara un cambio controlado" \
  --write-scope ".orchestrator-runtime/smoke-write" \
  --edit-ops-file /tmp/edit_ops.json \
  --fast
```

### 4. Safe operational command

```bash
python3 -m orchestrator.cli run --task examples/task.ops.json
```

Use when you want:
- shell execution
- environment checks
- safe local operations
- reproducible command logs

### 5. Install/setup workflow

```bash
python3 -m orchestrator.cli run --task examples/task.install-tool.json
```

Use when you want:
- setup help
- install command routing
- operational task tracking

### 6. Voice / TTS

```bash
python3 -m orchestrator.cli run --task examples/task.voice.json
```

Use when you want:
- local spoken summaries
- local TTS artifacts
- audio task pipelines

## What v1 already does for real

- real Crossref discovery for research
- real landing-page/PDF target validation
- real repo inspection and validation-command discovery
- real scoped file edits for coding tasks
- real shell execution for allowlisted ops commands
- real local macOS speech generation
- real task persistence and artifact storage
- real OpenClaw/Telegram launching through `orquesta-ai`

## Telegram / OpenClaw launcher

You can already launch general tasks from chat:

```text
orquesta research compara PaperFlow con herramientas similares
orquesta sistema ! pwd
orquesta codigo revisa el repo y dime los archivos clave
orquesta research; navega:https://example.com
orquesta sistema; abre excel
orquesta sistema; abre powerpoint
orquesta sistema; abre excel con /ruta/archivo.xlsx
```

For coding tasks with real edits, use semicolon directives:

```text
orquesta codigo; repo:paperflow; scope:README.md,docs; write:README.md::Nueva nota de prueba
```

You can also use a more natural shorthand:

```text
orquesta codigo; repo:paperflow; crea archivo docs/nota.txt: hola equipo
orquesta codigo; repo:paperflow; agrega en README.md: \nNueva linea
orquesta codigo; repo:paperflow; reemplaza en README.md: Texto viejo => Texto nuevo
```

Supported directives:

- `repo:<alias-o-ruta>`
- `scope:<ruta1,ruta2,...>`
- `articulos:<item1,item2,...>`
- `excel:<ruta.xlsx>`
- `url:<https://...>`
- `write:<ruta>::<contenido>`
- `append:<ruta>::<contenido>`
- `replace:<ruta>::<buscar>::<reemplazo>`
- `fast:true|false`

Review-style shortcut example:

```text
orquesta review; descargame estos articulos:https://.../paper.pdf,10.1000/xyz123; llename este excel:/ruta/template.xlsx
```

If you want the system to keep going through retries/fallbacks instead of stopping at the first failure, ask it that way:

```text
orquesta review; descargame estos articulos:...; llename este excel:/ruta/template.xlsx; no te detengas hasta terminar
```

The chat launcher now treats review, coding, and ops tasks as autonomous by default, with retries and partial-completion support when a step fails but the rest can still continue.

For fluid web navigation, use:

```text
orquesta research; navega:https://openai.com,https://example.com
```

That path uses a real browser-first flow when available, captures readable text plus top links, and falls back to HTTP parsing if the browser layer fails.

For installed Mac apps, use:

```text
orquesta sistema; abre excel
orquesta sistema; abre powerpoint
orquesta sistema; abre word
orquesta sistema; abre excel con /ruta/archivo.xlsx
orquesta sistema; crea excel en /Users/diegoalejandroidarragalopez/Desktop/reporte.xlsx
orquesta sistema; crea powerpoint en /Users/diegoalejandroidarragalopez/Desktop/resumen.pptx: Titulo | Punto 1 | Punto 2
orquesta sistema; cierra powerpoint
orquesta sistema; abre archivo /ruta/archivo.pdf
orquesta sistema; muestra carpeta /Users/diegoalejandroidarragalopez/Documents
```

The ops layer now supports terminal commands plus desktop app actions for installed apps like Excel, PowerPoint, Word, Brave, Telegram, WhatsApp, Preview, Keynote, Numbers, and Finder.

You can also chain several steps in one request:

```text
orquesta sistema; pwd; abre powerpoint; crea excel en /Users/diegoalejandroidarragalopez/Desktop/reporte.xlsx
```

Natural requests also work now without rigid command syntax:

```text
abre este excel
abre esta presentacion
resumime este pdf
llename este excel con estos articulos y no te detengas hasta terminar
hazme una presentacion powerpoint con el ultimo documento
```

When a request mentions "este/esta/ultimo/reciente" plus Excel, PDF, PowerPoint, or Word, the adapter looks in `~/.openclaw/media/inbound` first and routes the task to the right agent automatically.

Known repo aliases:

- `paperflow`
- `paperflow-ai`
- `default`
- `new-project`

## What is still scaffolded

- deep PDF text/table extraction
- broad unrestricted shell execution
- richer retries, budgets, and subtask orchestration
- richer web provider stack beyond the current baseline

## Suggested next upgrades

1. Add real PDF text/table extraction to `document-miner`.
2. Let `coder-builder` optionally apply patches in a controlled write scope.
3. Expand `ops-runner` beyond the v1 allowlist into a policy-driven command executor.
4. Add OpenAlex, Unpaywall, or PubMed enrichment to research flows.
5. Add a higher-level task launcher that can start these tasks directly from Telegram/OpenClaw.

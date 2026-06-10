# PaperFlow AI — Plan Maestro de Reestructuración

> **Norte:** una sola idea organiza todo el producto: *el flujo de trabajo del epidemiólogo
> que conduce una revisión sistemática viva*. Cada módulo, carpeta, endpoint y página
> existe solo si sirve a una etapa de ese flujo. Lo que no sirve, se elimina o se archiva.

```
Protocolo (PICO) → Búsqueda → Cribado (PRISMA) → Extracción → Riesgo de sesgo (RoB)
      → Síntesis (meta-análisis) → Certeza (GRADE) → Reporte / Escritura → Actualización viva
```

Estado de partida: la **Fase 0 ya está completada** (PR #228): CI verde en backend
(222 tests), frontend (123 tests), tsc, lint y build, con fallback local de
meta-análisis (inverse-variance / DerSimonian–Laird) para que la síntesis funcione
sin el contenedor R.

---

## 1. Principios rectores

1. **Jerarquía por dominio, no por tipo técnico.** El código se agrupa por etapa del
   pipeline de evidencia (search, screening, extraction, synthesis, writing), no por
   "services/" gigantes y planos.
2. **Local-first real.** Toda función núcleo debe funcionar sin servicios externos
   (patrón ya aplicado al meta-análisis: motor primario + fallback local). Grobid,
   R, Qdrant y Ollama mejoran el resultado; su ausencia degrada, nunca rompe.
3. **Provenance-first (el estándar del epidemiólogo).** Ningún número sin fuente:
   cada efecto extraído, cada claim de escritura y cada consulta clínica conserva
   `paper_id`, página, locator y confianza. Esto ya existe en extracción; el plan lo
   exige en *todas* las salidas.
4. **Minimalismo con horizonte.** Una sola forma de hacer cada cosa: un lockfile, un
   workflow de CI por suite, una vía de deploy soportada, un documento de arquitectura.
   Lo experimental vive en `attic/` o en otro repo, no en la raíz.
5. **Reproducibilidad.** Toda síntesis produce artefactos inmutables (CSV de efectos,
   script R, sessionInfo, figuras) — ya implementado; se extiende a cribado y GRADE.

---

## 2. Diagnóstico (auditoría 2026-06-10)

### Lo que funciona y se conserva tal cual
- Backend FastAPI vNext: routers limpios (`backend/app/api/`), modelos SQLAlchemy 2 async,
  pipeline extracción → matriz versionada → dataset derivado → meta-run → artefactos.
- Frontend React 19 + TS estricto: 24 suites de test, build y lint limpios.
- Suite de tests sólida (345 tests en total) y runner CI con timeout por archivo.
- Búsqueda federada (PubMed/Europe PMC/DOAJ + Unpaywall), Grobid, consultas clínicas
  con grounding y writing con trazabilidad de citas.

### Deuda estructural detectada (hechos, no opiniones)
| # | Hallazgo | Evidencia |
|---|----------|-----------|
| D1 | Base de datos SQLite **versionada en git** | `backend/paperflow.db` rastreado |
| D2 | Caché de vitest versionada en raíz | `node_modules/.vite/vitest/**/results.json` rastreado |
| D3 | **Dos lockfiles** en frontend (npm + pnpm) | `frontend/package-lock.json` + `frontend/pnpm-lock.yaml` |
| D4 | **CI duplicado**: la misma suite backend corre dos veces por PR | `ci.yml` (job Backend Tests) y `backend-ci.yml` (job pytest) |
| D5 | `orchestrator/` (+ `prompts/`, `registry/`, `examples/`, `config/router_rules.json`) **sin un solo import** desde backend/frontend | `grep` sin resultados fuera del propio paquete |
| D6 | **Cuatro vías de deploy** semi-mantenidas para una app local-first | `vercel.json` + `.vercel/`, `render.yaml`, `deploy-pages.yml`, `infra/` (helm+terraform) |
| D7 | Raíz contaminada con reportes puntuales y scripts muertos | `PHASE2_COMPLETION_REPORT.md`, `PROJECT_REVIEW.md`, `OPENCLAW_WORKFLOW.md`, `paperflow-workflow.md`, `run_test.py` (no hace nada), `nuke_and_rebuild.sh`, `.jules/` |
| D8 | Servicios backend planos: 30+ módulos en un solo nivel | `backend/app/services/` |
| D9 | Tests con dependencias ambientales (corregido el caso `LLM_PROVIDER`; patrón a vigilar) | PR #228 |
| D10 | El flujo PRISMA/cribado y GRADE no existen como módulos de primera clase pese a ser el corazón del dominio | revisión de routers/páginas |

---

## 3. Arquitectura objetivo

### 3.1 Repositorio (raíz minimalista)

```
paperflow-ai/
├── backend/            # API + dominio (única app Python)
├── frontend/           # Única app TS
├── r_engine/           # Servicio R (plumber) — motor primario de síntesis
├── deploy/             # TODO lo de despliegue, junto y jerárquico
│   ├── docker-compose.yml
│   ├── local/          # start.sh, stop.sh, scripts dev_*
│   └── observability/  # antes ops/ (grafana, prometheus)
├── docs/               # arquitectura, runbooks, ESTE plan
├── scripts/            # solo utilidades activas (backup/restore/smoke)
└── README.md · LICENSE · CONTRIBUTING.md · .env.example
```

- `orchestrator/`, `prompts/`, `registry/`, `examples/`, `benchmarks/`, `.jules/`:
  se mueven a `attic/` (o repo aparte `paperflow-agents`) hasta que algo los importe.
- Deploy soportado: **docker compose + scripts locales**. Vercel/Render/Pages/Helm/Terraform
  se archivan en `attic/deploy-experiments/` salvo decisión explícita de mantener uno.

### 3.2 Backend por dominios (jerarquía del pipeline)

```
backend/app/
├── api/                # routers HTTP delgados (sin lógica de negocio)
├── domains/
│   ├── protocol/       # NUEVO: PICO, criterios in/exclusión, registro de protocolo
│   ├── discovery/      # federated_search, pubmed, oa_resolvers, batch_download
│   ├── screening/      # NUEVO: cribado título/abstract + full-text, log PRISMA
│   ├── library/        # paper_service, paper_repo, pdf_processor, grobid, vector_index
│   ├── extraction/     # extraction_service, meta_extractor/, matrix_service
│   ├── synthesis/      # meta_runs_service (+ fallback local), datasets, quality_benchmarks
│   ├── appraisal/      # NUEVO: RoB 2 / ROBINS-I estructurado + GRADE por desenlace
│   ├── writing/        # writing_documents, writing_export, references_io, summarizer
│   └── clinical/       # clinical_consults, deep_research, chat_service
├── platform/           # transversales: auth, llm/, cache, jobs, storage, email,
│                       # permissions, runtime_health, audit, pagination
└── workers/            # RQ tasks (importa de domains/, nunca al revés)
```

Regla de dependencia: `api → domains → platform`. `domains` no se importan entre sí
salvo a través de modelos compartidos; `platform` no importa de `domains`.

### 3.3 Frontend: navegación que ES el pipeline

La barra lateral de proyecto se reordena para contar la historia de la revisión
(hoy es una lista plana de 10+ páginas):

```
1 Protocolo        → PICO, criterios (nuevo)
2 Buscar           → SearchPage
3 Cribar           → pantalla PRISMA (nuevo; hoy parcial en Papers)
4 Biblioteca       → PapersPage + ReaderPage
5 Extraer          → MetaPage (extracción) + MatrixPage
6 Evaluar          → RoB + GRADE (nuevo, datos ya existen en extracción)
7 Sintetizar       → MetaRunsPage + ArtifactsPage
8 Escribir         → WritingAssistantPage + ReferencesPage
9 Consultar        → ClinicalPage + DeepResearchPage
· Transversal      → Dashboard, Notas, Jobs, Settings
```

Páginas sin backend real o duplicadas (`AgentHubPage`, `CollaborationPage` si no hay
colaboración activa) se eliminan o se ocultan tras un flag hasta tener soporte.

---

## 4. Fases de ejecución

Cada fase termina con el mismo gate: **CI completo verde + build + lint + tsc**,
sin excepciones. Una fase no empieza hasta cerrar la anterior.

### ✅ Fase 0 — Línea base verde (HECHA, PR #228)
Estabilización de los 3 fallos de CI; fallback local de meta-análisis; suite 345/345.

### Fase 1 — Higiene del repositorio (bajo riesgo, alto retorno)
1. `git rm --cached backend/paperflow.db node_modules/...results.json` + reglas en `.gitignore`.
2. Eliminar `frontend/pnpm-lock.yaml` (CI usa `npm ci`); `run_test.py`; mover reportes
   puntuales de la raíz a `docs/history/`.
3. Unificar CI: borrar `backend-ci.yml`; `ci.yml` queda como única fuente de verdad.
4. Mover `ops/` → `deploy/observability/`, `docker-compose.yml` y scripts de arranque → `deploy/`
   (con symlinks o wrappers temporales para no romper hábitos).
5. Archivar en `attic/`: `orchestrator/`+`prompts/`+`registry/`+`examples/`, `.jules/`,
   configs de Vercel/Render/Helm/Terraform no usados.
6. Actualizar README a la nueva estructura.
   **Gate:** CI verde; `start.sh` (wrapper) sigue levantando el stack completo.

### Fase 2 — Backend jerárquico
1. Crear `app/domains/` y `app/platform/` y mover servicios por oleadas (una oleada =
   un dominio = un PR), dejando re-exports `from app.services.x import *` con
   `DeprecationWarning` durante una versión.
2. Routers a "controladores delgados": validación Pydantic + llamada a dominio.
3. Tests espejan la jerarquía (`tests/domains/synthesis/…`) y se purgan dependencias
   ambientales restantes (patrón D9: todo setting crítico se fija con `monkeypatch`).
   **Gate:** 0 imports circulares (verificar con `pydeps`/CI), suite completa verde.

### Fase 3 — Pipeline epidemiológico de primera clase (el diferencial)
1. **Protocolo:** modelo `ReviewProtocol` (pregunta PICO, criterios, desenlaces
   primarios/secundarios, plan de análisis). Todo proyecto nuevo nace con protocolo;
   la búsqueda y el cribado se validan contra él.
2. **Cribado PRISMA:** estados explícitos por registro (identificado → cribado →
   elegible → incluido, con razón de exclusión obligatoria); generación automática
   del **diagrama de flujo PRISMA 2020** como artefacto SVG (reutilizar el motor de
   SVG del forest plot).
3. **Appraisal:** RoB 2 / ROBINS-I como formularios estructurados por dominio de
   sesgo (los campos ya existen en `ExtractedStudy`); semáforo de tabla RoB exportable.
4. **GRADE:** por desenlace, partiendo de los datos del meta-run (I², IC, n.º estudios,
   sospecha de sesgo de publicación del funnel) + juicios manuales; salida = tabla
   *Summary of Findings* exportable a la escritura.
5. **Revisión viva:** job programado que re-ejecuta la búsqueda del protocolo y
   marca "nuevos registros pendientes de cribado".
   **Gate:** flujo e2e Playwright: protocolo → búsqueda → cribado → extracción →
   síntesis → SoF table, todo offline (fallbacks locales).

### Fase 4 — Frontend minimalista y fluido
1. Reordenar navegación según §3.3; eliminar/flag páginas muertas.
2. Un solo sistema de componentes (`src/ui/`): auditar estilos inline repetidos en
   páginas (patrón visible en `MetaRunsPage`/`ArtifactsPage`) y extraerlos.
3. Estados de carga/vacío/error uniformes (un componente `AsyncSection`).
4. Code-splitting ya existe; presupuesto: ningún chunk nuevo > 250 kB gzip.
   **Gate:** lint con 0 warnings, e2e smoke ampliado a las pantallas nuevas.

### Fase 5 — Calidad continua y rendimiento
1. Job e2e nocturno con stack docker completo (R real + Grobid) que valida que los
   fallbacks y los motores primarios producen resultados coherentes.
2. `benchmarks/` (casos de chat/extracción) se convierten en test de regresión de
   calidad con umbrales, ejecutado semanalmente.
3. Presupuestos de latencia: búsqueda < 2 s p95 (con caché), build matriz < 5 s
   para 100 estudios; medirlos en CI con los datos sintéticos existentes.
   **Gate:** dashboard de release (`docs/release_status.md`) actualizado y automático.

---

## 5. Métricas de éxito

| Métrica | Hoy | Objetivo |
|---|---|---|
| Jobs CI por PR (backend) | 2 duplicados | 1 |
| Entradas en la raíz del repo | 38 | ≤ 15 |
| Profundidad máx. `services/` plano | 30+ módulos/1 nivel | ≤ 10 módulos por dominio |
| Etapas del pipeline con módulo propio | 5/9 | 9/9 (protocolo, cribado, GRADE incluidos) |
| Funciones núcleo que sobreviven sin servicios externos | síntesis (desde Fase 0) | todas |
| Salidas con provenance verificable | extracción, writing | + cribado, RoB, GRADE, consultas |

## 6. Guardarraíles — qué NO hacer (para no perder el horizonte)

- **No** reescrituras big-bang: cada fase son PRs pequeños y reversibles sobre CI verde
  (la historia del repo muestra que los merges "big-bang" fueron los que rompieron master).
- **No** añadir features nuevas durante las Fases 1–2 (solo estructura).
- **No** introducir microservicios ni colas nuevas: el monolito modular + RQ basta.
- **No** acoplar el dominio a un proveedor LLM: todo pasa por `platform/llm` con
  fallback local, como ya hace el meta-análisis.
- **No** borrar nada con valor histórico: se archiva en `attic/` o `docs/history/`,
  y solo se elimina tras un ciclo de release sin que nadie lo eche de menos.

## 7. Orden y dependencias

```
Fase 1 (higiene) ──→ Fase 2 (backend jerárquico) ──→ Fase 3 (pipeline epidemiológico)
                                            │
                                            └──→ Fase 4 (frontend) ──→ Fase 5 (calidad)
```

Fase 1 es independiente y puede empezar ya. Fase 4 puede solaparse con Fase 3
una vez exista el dominio `screening/`. Cada fase ≈ 1–2 semanas de trabajo enfocado.

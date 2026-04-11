# PaperFlow Module Map (vNext)

This document tracks the current module boundaries after the vNext scope cut on `master`.

## Active modules

| Module | Role | Core routes |
| --- | --- | --- |
| `research` | PubMed discovery and import | `/search/*`, `/projects/{id}/library` |
| `library` | Paper repository and ingestion lifecycle | `/papers/*` |
| `reader` | Full text reading, annotations, evidence chat | `/chat/*`, `/notes/*` |
| `extraction` | Structured extraction records (study/effect/RoB) | `/meta/*`, `/extraction/*` |
| `matrix` | Versioned master extraction matrix | `/matrix/*` |
| `datasets` | Derived analytical datasets by preset | `/datasets/*` |
| `meta-runs` | Reproducible analysis runs + artifact catalog | `/meta/runs*`, `/artifacts/*` |
| `references` | Project bibliography management | `/references/*` |
| `writing` | Scientific writing assistant with grounded claims | `/writing/*` |
| `clinical-consults` | Rapid clinical consults with traceable evidence | `/clinical/consults*` |
| `jobs` | Background queue orchestration | `/jobs/*` |

## Removed modules (hard cut)

| Module | Status |
| --- | --- |
| `presentations` | Removed |
| `books` | Removed |
| `billing` | Removed |
| `clinical_sheets` | Removed (replaced by `clinical-consults`) |

## Data model direction

- Matrix-centric flow is canonical: extraction -> matrix versions -> derived datasets -> meta runs -> artifacts.
- Writing and clinical outputs must reference explicit source objects (`matrix_rows`, `meta_run_artifacts`, `reference_items`, `papers`/`pubmed`).
- No new backward compatibility layer should be introduced for removed modules.

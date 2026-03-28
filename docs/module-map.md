# PaperFlow AI Module Map

This document tracks the non-destructive transition from `ResearchConsole` to `PaperFlow AI`.

## Active product modules

| Current module | Product role now | Planned successor |
| --- | --- | --- |
| `projects` | Research project workspace | Keep and extend |
| `search` | Federated literature discovery | Keep and extend |
| `papers` | Project library and PDF ingestion | Keep and extend |
| `document pipeline` | Rich PDF parsing, OCR, layout and grounding | Keep and harden |
| `chat` | Evidence-grounded reader chat | Keep and harden |
| `meta` | Extraction workspace | Generalized extraction layer |
| `notes` | Project notes | Keep and extend |
| `references` | Citation library | New |
| `drafts` | Writing Studio groundwork | Keep and extend |
| `analysis` | Reproducible analysis orchestration | Keep and harden |
| `screening` | Review and PRISMA workflow | Keep and harden |
| `jobs` | Background processing queue | Keep and extend |

## Legacy modules

| Current module | Status | Replacement path |
| --- | --- | --- |
| `clinical` | Bridged/internal | `drafts` + Writing Studio via `POST /drafts/{id}/enhance-with-clinical` |
| `books` | Bridged/internal | private knowledge sources UI via `/knowledge` (backend `/books` kept for compatibility) |
| `presentations` | Optional/secondary | post-MVP |

## Data model migration rules

- Do not rename or drop legacy tables during the early transition.
- Add new document and reference entities in parallel.
- Prefer adapters over rewrites while UI routes are still shared.
- New user-facing surfaces should point to `PaperFlow AI` naming even when legacy models still exist internally.

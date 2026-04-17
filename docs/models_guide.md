# Model Guide — which LLM to use for what

PaperFlow AI is provider-agnostic. This guide documents the recommended model for
each workload in a **local-first, single-user** deployment and how to wire it up.

---

## 1. Default stack (recommended)

| Role | Provider | Model | Why |
|---|---|---|---|
| Chat / general reasoning | Ollama (local) | `qwen2.5-coder:7b` | Fast on an 8 GB GPU / 16 GB RAM, strong on structured output |
| Writing Assistant | Ollama | `qwen2.5-coder:7b` | Same model; keeps style consistent between chat and writing |
| Embeddings (Qdrant) | Ollama | `nomic-embed-text:latest` | 768-dim, balanced speed / quality |
| Vision (figures, table OCR) | Ollama | `qwen3-vl:8b` | Only pulled on demand; skip if no GPU |
| Extraction worker | Ollama | `qwen2.5-coder:7b` | Accepts tight JSON schemas via tool-like prompting |

All of the above run locally — no network calls leave your machine.

Install / update:

```bash
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text:latest
# optional
ollama pull qwen3-vl:8b
```

---

## 2. Optional cloud fallback (Claude)

If a box can't run the local models comfortably, or you want premium writing
quality on specific sections, set `ANTHROPIC_API_KEY` and pick one of:

| Tier | Model ID | When to use |
|---|---|---|
| Max quality | `claude-opus-4-7` | Final polish of a cover letter or grant proposal |
| Balanced (default) | `claude-sonnet-4-6` | Day-to-day writing & synthesis |
| Fast & cheap | `claude-haiku-4-5-20251001` | Bulk extraction, short consults, quick rewrites |

In `.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
LLM_PROVIDER=auto_local          # Ollama first, Claude as fallback
```

Set `LLM_PROVIDER=cloud` to skip local models entirely.

---

## 3. OpenClaw routing (advanced)

`LLM_PROVIDER=auto_local` uses the OpenClaw router: Ollama is tried first, Claude is
used only if the local call fails or times out. This is the configuration the
first-time setup script installs and matches the _Local only_ runtime mode in
**Settings → Runtime**.

The three runtime presets available in the UI:

- **Local only** → Ollama primary, Ollama fallback (no cloud call ever).
- **Hybrid** → Ollama primary, Claude fallback (triggered on local failure).
- **Cloud** → Claude primary, Ollama fallback (internet required).

---

## 4. Hardware rules of thumb

| VRAM | Recommendation |
|---|---|
| ≥ 16 GB | `qwen2.5-coder:7b` + `qwen3-vl:8b` comfortably in parallel |
| 8–16 GB | Run `qwen2.5-coder:7b` alone, skip vision model |
| < 8 GB (CPU only) | Use Hybrid mode with Claude Haiku for anything non-trivial |

Embedding calls are cheap everywhere; keep `nomic-embed-text` enabled.

---

## 5. Checking which model answered a request

The Reader, Writing and Clinical surfaces return the `model` field in API
responses and show it inline next to the assistant output. `Settings → LLM
Services status` also reports the currently active model per surface (chat /
writing / vision / embedding).

---

## 6. Swapping models safely

1. Pull the new model with `ollama pull <name>`.
2. Edit `.env`:
   - `PAPERFLOW_CHAT_MODEL=<name>` (general chat)
   - `PAPERFLOW_WRITING_MODEL=<name>` (Writing Assistant)
   - `PAPERFLOW_EMBEDDING_MODEL=<name>` (vectors — re-indexes on next search)
   - `PAPERFLOW_VISION_MODEL=<name>` (figures / OCR)
3. Restart the backend: `docker compose restart api worker`.
4. Smoke-test from **Settings → LLM Services status → Refresh**.

If latency explodes after a swap, check `docker stats` for the Ollama container —
model swaps evict the previous one from RAM and the first call pays the load
cost.

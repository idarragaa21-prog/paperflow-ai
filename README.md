<div align="center">

# PaperFlow AI

**AI-powered research workspace — local-first, private by design.**

Search, extract, analyze and write academic papers with a full-stack platform
that runs entirely on your machine. No cloud sync, no subscriptions, no commercial billing, and no data leaving your computer by default.

[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178c6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169e1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Live Demo](https://idarragaa21-prog.github.io/paperflow-ai/) · [Quick Start](#quick-start) · [Architecture](#architecture) · [Contributing](#contributing)

</div>

---

## Features

| Module | Description |
|--------|-------------|
| **Paper Library** | Upload, import by DOI, batch download from PubMed. Status tracking, favorites, full-text processing via Grobid. |
| **PubMed Search** | Federated search with result cards, batch import, and automatic open-access resolution via Unpaywall. |
| **AI Reader** | Read PDFs with an integrated AI chat grounded in the document. Highlights, annotations, chat history. |
| **Extraction Workspace** | Structured study/effect/RoB extraction with provenance and validation warnings. |
| **Master Matrix** | Versioned extraction matrix with export to XLSX/CSV/JSON/XML. |
| **Meta Runs** | Preset-based derived datasets and reproducible analysis runs with artifact catalog. |
| **Clinical Consults** | Rapid clinical consults (`brief`, `standard`, `deep`) grounded in project evidence and/or PubMed. |
| **Writing Assistant** | IMRAD-oriented scientific writing with claim-to-source traceability from matrix, meta runs and references. |
| **References** | BibTeX export, APA clipboard copy, DOI import, project-scoped reference management. |
| **Dashboard** | Project-level stats, quick navigation, recent activity overview. |
| **Mobile** | Fully responsive with hamburger drawer, mobile topbar, and touch-friendly interactions. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React 19)                   │
│            TypeScript · Vite · Zustand · Mermaid         │
│                   Port 5173                              │
└───────────────────────┬─────────────────────────────────┘
│ HTTP (REST + cookies)
┌───────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                      │
│   vNext API routers · async services · Auth middleware     │
│                    Port 8000                              │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ Postgres │  Redis   │  Qdrant  │  MinIO   │   Grobid    │
│  :5432   │  :6379   │  :6333   │  :9000   │   :8070     │
│    DB    │ Jobs/RQ  │ Vectors  │ Storage  │  PDF Parse  │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│      R Engine (:8010) · OpenClaw + Ollama (Local AI)      │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript 5.9, Vite 7, Zustand, React Router 7, Mermaid, Axios |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Database | PostgreSQL 16 (primary), Redis 7 (jobs + cache), Qdrant (vector search) |
| Storage | MinIO (S3-compatible object storage) or local filesystem |
| AI/ML | Ollama (local LLM), OpenClaw (multi-vendor routing), Anthropic Claude (optional) |
| PDF | Grobid 0.8.1 (scientific PDF parsing), PyMuPDF, pdfplumber |
| Statistics | R 4.4.2 via plumber API (meta, metafor, broom, survival) |
| Auth | JWT (HttpOnly cookies), bcrypt, CSRF protection, rate limiting (SlowAPI) |

---

## Quick Start

### Prerequisites

- **Docker Desktop** (for infrastructure services)
- **Python 3.11** (`brew install python@3.11` on macOS)
- **Node.js `^20.19.0` or `>=22.12.0`** and npm
- **Git**

### Option A: One-command startup

```bash
git clone https://github.com/idarragaa21-prog/paperflow-ai.git
cd paperflow-ai
chmod +x start.sh
./start.sh
```

This will:
1. Start all Docker services (Postgres, Redis, Qdrant, MinIO, Grobid, R engine)
2. Create a Python virtualenv and install dependencies
3. Run database migrations
4. Create a demo user
5. Start the backend API and frontend dev server

Open **http://127.0.0.1:5173** and sign in with `demo@paperflow.ai` / `demo1234`.

### Option B: Step-by-step (development)

```bash
# 1. Clone and configure
git clone https://github.com/idarragaa21-prog/paperflow-ai.git
cd paperflow-ai
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. Start infrastructure
docker compose up -d postgres redis qdrant minio minio-init grobid r-engine

# 3. Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.create_user --email you@example.com --password yourpassword
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Option C: Helper scripts (macOS)

```bash
# Start everything (background processes)
scripts/dev_up.sh

# Stop everything
scripts/dev_down.sh
```

---

## Configuration

### Environment Variables

Copy `.env.example` files and adjust as needed:

```bash
cp .env.example .env              # Docker Compose infra
cp backend/.env.example backend/.env   # Backend application
cp frontend/.env.example frontend/.env # Frontend (optional)
```

Key variables in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/paperflow_ai` | PostgreSQL connection |
| `SECRET_KEY` | `CHANGE_ME` | JWT signing secret — **change in production** |
| `STORAGE_BACKEND` | `s3` | `s3` (MinIO) or `filesystem` |
| `LLM_PROVIDER` | `auto_local` | `auto_local`, `openclaw`, `ollama`, `direct_claude` |
| `PAPERFLOW_CHAT_MODEL` | `qwen2.5-coder:7b` | Ollama model for paper chat |
| `PAPERFLOW_WRITING_MODEL` | `qwen2.5-coder:7b` | Ollama model for writing + clinical synthesis |
| `PAPERFLOW_VISION_MODEL` | `qwen3-vl:8b` | Ollama model for visual/PDF tasks |
| `GROBID_ENABLED` | `true` | Enable PDF parsing via Grobid |

Production deploy notes:

- Set `BACKEND_CORS_ORIGINS` to the real frontend origin.
- If frontend and backend live on different origins, use `COOKIE_SAMESITE=none` over HTTPS.
- Do not leave `VITE_API_BASE_URL` implicit in production.
- `vercel.json` must never rewrite `/api/*` to `index.html`.
- Invitation emails are optional. Set `MAIL_ENABLED=true` plus SMTP settings to send real email invites and password reset codes; otherwise PaperFlow falls back to secure manual links.

### LLM Configuration

PaperFlow AI supports multiple LLM backends:

1. **`auto_local` (default):** OpenClaw as primary router with automatic fallback to local Ollama.
2. **OpenClaw:** Multi-vendor routing gateway for Groq, Gemini, DeepSeek, etc.
3. **Ollama:** Fully local execution for chat/summarization + embeddings.
4. **Direct Claude:** Set `ANTHROPIC_API_KEY` in `backend/.env`.

---

## Project Structure

```
paperflow-ai/
├── backend/                    # Python FastAPI application
│   ├── app/
│   │   ├── api/                # FastAPI routers and HTTP endpoints
│   │   ├── core/               # Security, storage, logging, telemetry
│   │   ├── middleware/         # Auth, CSRF, rate limiting
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic, search, extraction, analysis
│   │   │   ├── llm/           # LLM routing (OpenClaw/Ollama/Claude adapters)
│   │   │   └── meta_extractor/ # Meta-analysis data extraction
│   │   ├── workers/           # Background job processing (RQ)
│   │   └── main.py            # FastAPI app entry point
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend test suite
│   └── requirements.txt
├── frontend/                   # React TypeScript application
│   ├── src/
│   │   ├── pages/             # App pages and workflows
│   │   ├── components/        # Layout and shared UI building blocks
│   │   ├── services/          # API client, auth, demo mode
│   │   ├── store/             # Zustand state management
│   │   ├── test/              # Frontend unit/integration tests
│   │   └── ui/                # Reusable UI primitives
│   └── package.json
├── r_engine/                   # R statistical analysis service
│   ├── Dockerfile
│   └── plumber.R
├── scripts/                    # Dev helper scripts
├── docker-compose.yml          # Infrastructure services
├── start.sh                    # One-command local startup
└── stop.sh                     # Graceful shutdown
```

---

## API Overview

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| Auth | `/auth` | login, logout, refresh, me, change-password |
| Projects | `/projects` | CRUD, dashboard stats, archive, export-zip |
| Papers | `/papers` | upload, download, process, favorites, citations |
| Search | `/search` | PubMed, federated search |
| Chat | `/chat` | AI paper chat with grounding |
| Extraction | `/meta`, `/extraction` | Study/effect/RoB extraction workflows |
| Matrix | `/matrix` | build, list versions, inspect, export (`xlsx/csv/json/xml`) |
| Datasets | `/datasets` | derive dataset from matrix versions |
| Meta Runs | `/meta/runs` | run preset analyses, list runs and artifacts |
| Artifacts | `/artifacts` | immutable artifact download by id |
| Clinical | `/clinical` | clinical consults create/list/get |
| Writing | `/writing` | writing documents, section generation, citation resolution |
| References | `/references` | Import, export BibTeX/APA |
| Notes | `/notes` | CRUD per project |
| Jobs | `/jobs` | Background job tracking, cancel |

Full API docs available at **http://127.0.0.1:8000/docs** when backend is running.

---

## Development

### Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -q                    # Run all tests
pytest tests/test_vnext_core_endpoints.py -v  # vNext end-to-end flow

# Local AI sanity (OpenClaw + Ollama)
cd ..
./scripts/check_local_ai.sh
```

### Building Frontend

```bash
cd frontend
npm run build    # Production build → dist/
npm run lint     # ESLint check
```

### Database Migrations

```bash
cd backend
source .venv/bin/activate
alembic upgrade head         # Apply all migrations
alembic downgrade -1         # Rollback one migration
alembic revision -m "desc"   # Create new migration
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python3` points to 3.14+ | Use `python3.11 -m venv backend/.venv` explicitly |
| Alembic "Can't locate revision" | `docker compose down -v` to reset DB volumes, then re-run migrations |
| Grobid "platform mismatch" warning | Normal on Apple Silicon — runs via emulation, slightly slower |
| Container name conflict | `docker rm -f paperflow-grobid` then retry |
| `plumber` R package fails | Ensure `libsodium-dev` is in `r_engine/Dockerfile` |
| Frontend can't reach backend | Check `VITE_API_BASE_URL` in `frontend/.env` or use the vite proxy |

### Nuclear Reset

If everything is broken, this cleans and restarts from zero:

```bash
cd ~/paperflow-ai
docker compose down -v --remove-orphans
docker rm -f $(docker ps -aq --filter name=paperflow) 2>/dev/null
docker volume prune -f
rm -rf backend/.venv frontend/node_modules
python3.11 -m venv backend/.venv
./start.sh
```

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit changes (`git commit -m 'feat: add my feature'`)
4. Push to branch (`git push origin feat/my-feature`)
5. Open a Pull Request

## Release Baseline

`master` is the only release-tracked branch. Divergent `feat/*`, `fix/*`, `audit/*`, `claude/*` or `codex/*` branches should not be mass-merged into release; reintegrate only by fresh validation against current `master` or selective cherry-picks.
The operational release checklist lives in [docs/release_status.md](docs/release_status.md).

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ☕ by <a href="https://github.com/idarragaa21-prog">Diego Alejandro Idarraga</a></sub>
</div>

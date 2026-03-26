<div align="center">

# PaperFlow AI

**AI-powered research workspace — local-first, private by design.**

Search, extract, analyze and write academic papers with a full-stack platform
that runs entirely on your machine. No cloud sync, no subscriptions, no data leaving your computer.

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
| **Meta-Analysis** | Data extraction with AI, effect size calculation, risk of bias assessment (RoB), Excel/CSV export. R engine for statistical analysis. |
| **Clinical Sheets** | Generate UpToDate-style clinical evidence summaries using a multi-pass LLM pipeline. Export to DOCX/PDF. |
| **Literature Drafts** | AI-assisted scientific writing with inline editing, citation resolution, and HTML export. |
| **References** | BibTeX export, APA clipboard copy, DOI import, project-scoped reference management. |
| **Presentations** | Auto-generate slide decks from project papers using customizable templates. |
| **Books & Scans** | Index and search across book collections and scanned documents. |
| **Screening** | PRISMA-aligned title/abstract screening with eligibility criteria and batch workflows. |
| **Analysis** | Statistical analysis orchestration through R engine (regression, group comparison, descriptives). |
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
│     17 API routers · 105+ endpoints · Auth middleware     │
│                    Port 8000                              │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ Postgres │  Redis   │  Qdrant  │  MinIO   │   Grobid    │
│  :5432   │  :6379   │  :6333   │  :9000   │   :8070     │
│    DB    │ Jobs/RQ  │ Vectors  │ Storage  │  PDF Parse  │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│              R Engine (:8010) · Ollama (LLM)             │
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
- **Node.js 18+** and npm
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

Open **http://localhost:5173** and sign in with `demo@paperflow.ai` / `demo1234`.

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
| `LLM_PROVIDER` | `openclaw` | `openclaw` or `direct_claude` |
| `PAPERFLOW_CHAT_MODEL` | `qwen2.5:7b` | Ollama model for paper chat |
| `GROBID_ENABLED` | `true` | Enable PDF parsing via Grobid |

Production deploy notes:

- Set `BACKEND_CORS_ORIGINS` to the real frontend origin.
- If frontend and backend live on different origins, use `COOKIE_SAMESITE=none` over HTTPS.
- Do not leave `VITE_API_BASE_URL` implicit in production.
- `vercel.json` must never rewrite `/api/*` to `index.html`.

### LLM Configuration

PaperFlow AI supports multiple LLM backends:

1. **Ollama (default, free):** Install [Ollama](https://ollama.com), pull a model (`ollama pull qwen2.5:7b`), and it works out of the box.
2. **OpenClaw:** Multi-vendor routing gateway for Groq, Gemini, DeepSeek, etc.
3. **Direct Claude:** Set `ANTHROPIC_API_KEY` in `backend/.env`.

---

## Project Structure

```
paperflow-ai/
├── backend/                    # Python FastAPI application
│   ├── app/
│   │   ├── api/                # 17 API routers (105+ endpoints)
│   │   ├── core/               # Security, storage, logging, telemetry
│   │   ├── middleware/         # Auth, CSRF, rate limiting
│   │   ├── models/            # 19 SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # Business logic (56 service modules)
│   │   │   ├── clinical/      # Clinical PRO pipeline (multi-pass LLM)
│   │   │   ├── llm/           # LLM routing, presets, ensemble
│   │   │   └── meta_extractor/ # Meta-analysis data extraction
│   │   ├── workers/           # Background job processing (RQ)
│   │   └── main.py            # FastAPI app entry point
│   ├── alembic/               # Database migrations (11 revisions)
│   ├── tests/                 # 39 test files (78 tests)
│   └── requirements.txt
├── frontend/                   # React TypeScript application
│   ├── src/
│   │   ├── pages/             # 18 page components
│   │   ├── components/        # Layout, clinical, meta-analysis
│   │   ├── domain/            # Clinical domain logic
│   │   ├── services/          # API client, auth, demo mode
│   │   ├── store/             # Zustand state management
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
| Meta | `/meta` | Studies, effects, RoB, exports |
| Clinical | `/clinical` | Sheets CRUD, generate, versions, export DOCX/PDF |
| References | `/references` | Import, export BibTeX/APA |
| Drafts | `/drafts` | AI writing, section generation, citation resolution |
| Presentations | `/presentations` | Generate slide decks |
| Extraction | `/extraction` | Data extraction templates and records |
| Screening | `/screening` | Batches, decisions, eligibility criteria |
| Analysis | `/analysis` | R engine analysis runs |
| Books | `/books` | Index, scan folder, reindex |
| Notes | `/notes` | CRUD per project |
| Jobs | `/jobs` | Background job tracking, cancel |

Full API docs available at **http://localhost:8000/docs** when backend is running.

---

## Development

### Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -q                    # Run all tests
pytest tests/test_clinical_pro.py -v  # Specific test file
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

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ☕ by <a href="https://github.com/idarragaa21-prog">Diego Alejandro Idarraga</a></sub>
</div>

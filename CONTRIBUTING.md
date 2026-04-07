# Contributing to PaperFlow AI

Thank you for your interest in contributing! This guide covers local setup, coding conventions, and the pull-request workflow.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local setup](#local-setup)
3. [Running the services](#running-the-services)
4. [Project structure](#project-structure)
5. [Coding conventions](#coding-conventions)
6. [Testing](#testing)
7. [Pull-request workflow](#pull-request-workflow)

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker & Docker Compose | 24+ |
| Node.js | 20+ |
| Python | 3.11+ |
| uv (Python package manager) | latest |

---

## Local setup

```bash
# 1. Clone the repository
git clone https://github.com/idarragaa21-prog/paperflow-ai.git
cd paperflow-ai

# 2. Copy environment files and fill in your values
cp .env.example .env
cp backend/.env.example backend/.env   # if it exists

# 3. Start infrastructure services (Postgres, Redis, Qdrant, MinIO, Grobid, R-engine)
docker compose up -d postgres redis qdrant minio minio-init grobid r-engine

# 4. Install backend dependencies
cd backend
uv sync
# Apply DB migrations
uv run alembic upgrade head
cd ..

# 5. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Running the services

### Backend API (FastAPI)

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

### Background worker (RQ)

```bash
cd backend
uv run python -m app.workers.worker
```

### Frontend (Vite dev server)

```bash
cd frontend
npm run dev
# Opens at http://localhost:5173
```

### Full stack with Docker

```bash
docker compose --profile full up --build
```

---

## Project structure

```
paperflow-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (one file per domain)
│   │   ├── core/         # Logger, storage, redis, security
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic (no HTTP concerns)
│   │   └── workers/      # RQ background jobs (split by domain)
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/   # Shared React components
│   │   ├── pages/        # Route-level page components
│   │   ├── services/     # API client (axios) and utilities
│   │   ├── store/        # Zustand global state stores
│   │   ├── types/        # Shared TypeScript types
│   │   └── ui/           # Primitive UI components (Toast, Dialog, Skeleton)
│   └── src/test/         # Vitest unit tests
├── docs/                 # Architecture and API documentation
├── docker-compose.yml
└── CONTRIBUTING.md       # This file
```

---

## Coding conventions

### Backend (Python)

- **Style**: Follow PEP 8; use `ruff` for formatting and linting.
- **Typing**: All public functions must have type annotations.
- **Async**: All database and I/O operations must be `async`.
- **Errors**: Raise `HTTPException` in routers; raise domain exceptions in services.
- **Logging**: Use `from app.core.logger import logger` (loguru), not stdlib `print`.
- **Worker jobs**: Each job module lives in `backend/app/workers/tasks_<domain>.py`. The shared loop helper is in `_run_coro.py`. `tasks.py` is a backward-compat re-export; do not add logic there.

### Frontend (TypeScript / React)

- **State**: Prefer `@tanstack/react-query` for server state. Use Zustand stores (`store/`) only for cross-page client state.
- **Types**: All API types live in `src/types/api.ts`; import from there, do not redeclare locally.
- **Error handling**: Global errors (403/429/5xx) are pushed through `uiStore` → `GlobalErrorBridge` → `ToastProvider`. Per-operation errors can stay local.
- **Components**: Keep pages thin — extract reusable logic into `hooks/` and reusable UI into `components/` or `ui/`.
- **CSS**: Global design tokens in `index.css`; component-scoped styles via inline styles or `App.css`.

---

## Testing

### Backend

```bash
cd backend
uv run pytest                        # all tests
uv run pytest tests/unit/            # unit tests only
uv run pytest --cov=app --cov-report=term-missing  # with coverage
```

### Frontend

```bash
cd frontend
npm test                 # run all Vitest tests once
npm run test:watch       # watch mode
```

---

## Pull-request workflow

1. **Branch naming**: `feat/<short-description>`, `fix/<short-description>`, `chore/<short-description>`.
2. **Commit messages**: Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
3. **Before opening a PR**:
   - All existing tests pass locally.
   - New code has corresponding tests.
   - `ruff check .` passes in `backend/`.
   - `npm run lint` passes in `frontend/`.
4. **PR description**: Explain *what* changed and *why*. Link any related issues.
5. **Review**: At least one approval is required before merging to `main`.

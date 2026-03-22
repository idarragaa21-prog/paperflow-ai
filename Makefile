.PHONY: test test-backend test-frontend lint typecheck install dev

# ── Backend ───────────────────────────────────────────────────────────────────

test-backend:
	cd backend && python -m pytest tests/ -q --no-header

test-backend-v:
	cd backend && python -m pytest tests/ -v --no-header

# ── Frontend ──────────────────────────────────────────────────────────────────

test-frontend:
	cd frontend && npx vitest run

test-frontend-v:
	cd frontend && npx vitest run --reporter=verbose

# ── All tests ─────────────────────────────────────────────────────────────────

test: test-backend test-frontend

# ── Lint / type-check ─────────────────────────────────────────────────────────

lint:
	cd frontend && npm run lint

typecheck:
	cd frontend && npx tsc --noEmit

# ── Install ───────────────────────────────────────────────────────────────────

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# ── Dev servers ───────────────────────────────────────────────────────────────

dev: dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

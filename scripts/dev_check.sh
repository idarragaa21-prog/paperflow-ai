#!/usr/bin/env bash
# dev_check.sh — verifica el estado local del proyecto PaperFlow AI
# Uso: ./scripts/dev_check.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

# Color helpers (si el terminal lo soporta)
if [ -t 1 ] && command -v tput &>/dev/null && tput colors &>/dev/null && [ "$(tput colors)" -ge 8 ]; then
  GREEN="\033[0;32m"
  RED="\033[0;31m"
  YELLOW="\033[0;33m"
  RESET="\033[0m"
else
  GREEN="" RED="" YELLOW="" RESET=""
fi

ok()   { echo -e "${GREEN}[PASS]${RESET} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}[FAIL]${RESET} $1"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}[INFO]${RESET} $1"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " PaperFlow AI — dev_check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Docker services ────────────────────────────────────────
info "Checking Docker services..."

check_container() {
  local name="$1"
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "$name"; then
    ok "Docker container '$name' is running"
  else
    fail "Docker container '$name' is NOT running (run: docker compose up -d $name)"
  fi
}

if ! command -v docker &>/dev/null; then
  fail "Docker not installed or not in PATH"
else
  check_container "paperflow-postgres"
  check_container "paperflow-redis"
  check_container "paperflow-qdrant"
fi

# ── 2. Backend health ─────────────────────────────────────────
info "Checking backend health (:8000)..."
if curl -sf http://127.0.0.1:8000/health -o /dev/null 2>/dev/null; then
  ok "Backend responds on :8000/health"
else
  fail "Backend not responding on :8000 (is uvicorn running?)"
fi

# ── 3. Backend tests ──────────────────────────────────────────
info "Running pytest..."
VENV_PYTHON="${REPO_ROOT}/backend/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
  fail "Backend venv not found at backend/.venv (run: python3.11 -m venv backend/.venv && pip install -r backend/requirements.txt)"
else
  if (cd "${REPO_ROOT}/backend" && "${VENV_PYTHON}" -m pytest -q --tb=short 2>&1 | tail -5); then
    ok "pytest passed"
  else
    fail "pytest FAILED"
  fi
fi

# ── 4. Frontend lint ──────────────────────────────────────────
info "Running frontend lint..."
if ! command -v npm &>/dev/null; then
  fail "npm not found in PATH"
else
  if (cd "${REPO_ROOT}/frontend" && npm run lint 2>&1 | tail -5); then
    ok "eslint passed"
  else
    fail "eslint FAILED"
  fi
fi

# ── 5. Frontend build ─────────────────────────────────────────
info "Running frontend build..."
if (cd "${REPO_ROOT}/frontend" && npm run build 2>&1 | tail -5); then
  ok "frontend build passed"
else
  fail "frontend build FAILED"
fi

# ── Summary ───────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${GREEN}PASS: ${PASS}${RESET}   ${RED}FAIL: ${FAIL}${RESET}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

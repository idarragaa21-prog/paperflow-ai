#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.dev_logs"
mkdir -p "$LOG_DIR"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

copy_if_missing() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$dst" ]] && [[ -f "$src" ]]; then
    cp "$src" "$dst"
    echo "[dev_up] created $dst from template"
  fi
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-30}"
  for _ in $(seq 1 "$attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[dev_up] $label is ready"
      return 0
    fi
    sleep 2
  done
  echo "[dev_up] $label did not become ready: $url" >&2
  return 1
}

start_if_not_running() {
  if [[ $# -lt 2 ]]; then
    echo "[dev_up] internal error: start_if_not_running requires: <name> <command...>" >&2
    return 2
  fi

  local name="$1"; shift
  local pid_file="$LOG_DIR/${name}.pid"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[dev_up] $name already running (pid=$pid)"
      return 0
    fi
  fi

  echo "[dev_up] starting $name..."
  nohup "$@" >"$LOG_DIR/${name}.log" 2>&1 &
  echo $! >"$pid_file"
  echo "[dev_up] $name started (pid=$(cat "$pid_file"))"
}

copy_if_missing "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
copy_if_missing "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
copy_if_missing "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"

echo "[dev_up] starting infrastructure with docker compose..."
(cd "$ROOT_DIR" && docker compose up -d postgres redis qdrant minio minio-init grobid r-engine)

wait_for_url "http://127.0.0.1:8010/health" "r-engine"
wait_for_url "http://127.0.0.1:8070/api/isalive" "grobid"
wait_for_url "http://127.0.0.1:9000/minio/health/live" "minio"

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "[dev_up] backend/.venv is missing; create it before using dev_up" >&2
  exit 1
fi

echo "[dev_up] applying migrations..."
(cd "$BACKEND_DIR" && source .venv/bin/activate && alembic upgrade head)

start_if_not_running backend bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && exec uvicorn app.main:app --host 127.0.0.1 --port 8000"
start_if_not_running worker bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && exec python -m app.workers.worker"
start_if_not_running frontend bash -lc "cd '$FRONTEND_DIR' && exec npm run dev -- --host 127.0.0.1 --port 5173"

wait_for_url "http://127.0.0.1:8000/health" "backend"

echo "[dev_up] URLs:"
echo "  backend:  http://127.0.0.1:8000"
echo "  frontend: http://127.0.0.1:5173"

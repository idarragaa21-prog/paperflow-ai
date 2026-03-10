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
  local sleep_seconds="${4:-2}"
  for _ in $(seq 1 "$attempts"); do
    if curl --max-time 5 -fsS "$url" >/dev/null 2>&1; then
      echo "[dev_up] $label is ready"
      return 0
    fi
    sleep "$sleep_seconds"
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

stop_app_process() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[dev_up] restarting $name (pid=$pid)"
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
}

copy_if_missing "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
copy_if_missing "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
copy_if_missing "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"

export STORAGE_BACKEND="${PAPERFLOW_RUNTIME_STORAGE_BACKEND:-s3}"
export S3_ENDPOINT_URL="${S3_ENDPOINT_URL:-http://127.0.0.1:${MINIO_PORT:-9000}}"
export S3_ACCESS_KEY="${S3_ACCESS_KEY:-${MINIO_ROOT_USER:-paperflow}}"
export S3_SECRET_KEY="${S3_SECRET_KEY:-${MINIO_ROOT_PASSWORD:-paperflow123}}"
export S3_BUCKET="${S3_BUCKET:-paperflow-artifacts}"
export PAPERFLOW_DISABLE_DOTENV=1

required_services=(postgres redis qdrant ollama minio minio-init grobid r-engine)
optional_services=(prometheus grafana)

echo "[dev_up] starting infrastructure with docker compose..."
(cd "$ROOT_DIR" && docker compose up -d "${required_services[@]}")

if [[ "${PAPERFLOW_START_OPTIONAL_SERVICES:-0}" == "1" ]]; then
  echo "[dev_up] starting optional observability services..."
  (cd "$ROOT_DIR" && docker compose --profile full up -d "${optional_services[@]}")
fi

wait_for_url "http://127.0.0.1:9000/minio/health/live" "minio"
wait_for_url "http://127.0.0.1:6333/collections" "qdrant"
wait_for_url "http://127.0.0.1:11434/api/tags" "ollama"
wait_for_url "http://127.0.0.1:8010/health" "r-engine"
wait_for_url "http://127.0.0.1:8070/api/isalive" "grobid" 180 5

if [[ "${PAPERFLOW_START_OPTIONAL_SERVICES:-0}" == "1" ]]; then
  wait_for_url "http://127.0.0.1:9090/-/ready" "prometheus"
  wait_for_url "http://127.0.0.1:3001/api/health" "grafana"
fi

if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  echo "[dev_up] backend/.venv is missing; create it before using dev_up" >&2
  exit 1
fi

echo "[dev_up] applying migrations..."
(cd "$BACKEND_DIR" && source .venv/bin/activate && alembic upgrade head)

# Force app-service restart so backend/frontend/workers always inherit the same runtime env.
stop_app_process frontend
stop_app_process worker-analysis
stop_app_process worker-presentations
stop_app_process worker-documents
stop_app_process backend
pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8000" 2>/dev/null || true
pkill -f "python -m app.workers.worker" 2>/dev/null || true
pkill -f "vite --host 127.0.0.1 --port 5173" 2>/dev/null || true

start_if_not_running backend bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && exec uvicorn app.main:app --host 127.0.0.1 --port 8000"
start_if_not_running worker-documents bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && export WORKER_QUEUES=documents OTEL_SERVICE_NAME=paperflow-worker-documents && exec python -m app.workers.worker"
start_if_not_running worker-presentations bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && export WORKER_QUEUES=presentations OTEL_SERVICE_NAME=paperflow-worker-presentations && exec python -m app.workers.worker"
start_if_not_running worker-analysis bash -lc "cd '$BACKEND_DIR' && source .venv/bin/activate && export WORKER_QUEUES=analysis OTEL_SERVICE_NAME=paperflow-worker-analysis && exec python -m app.workers.worker"
start_if_not_running frontend bash -lc "cd '$FRONTEND_DIR' && exec npm run dev -- --host 127.0.0.1 --port 5173"

wait_for_url "http://127.0.0.1:8000/health" "backend" 120 2
if [[ -x "$ROOT_DIR/scripts/dev_check.sh" ]]; then
  "$ROOT_DIR/scripts/dev_check.sh"
fi

echo "[dev_up] URLs:"
echo "  backend:  http://127.0.0.1:8000"
echo "  frontend: http://127.0.0.1:5173"
echo "  prometheus: http://127.0.0.1:${PROMETHEUS_PORT:-9090}"
echo "  grafana: http://127.0.0.1:${GRAFANA_PORT:-3001}"

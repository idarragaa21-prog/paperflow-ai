#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.dev_logs"

stop_by_pidfile() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    echo "[dev_down] $name: no pidfile"
    return 0
  fi

  local pid
  pid="$(cat "$pid_file" || true)"
  if [[ -z "$pid" ]]; then
    echo "[dev_down] $name: empty pidfile"
    rm -f "$pid_file"
    return 0
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "[dev_down] stopping $name (pid=$pid)…"
    kill "$pid" || true
    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
      echo "[dev_down] $name still running; sending SIGKILL"
      kill -9 "$pid" || true
    fi

    # Safety net: kill any direct children (should be none if dev_up uses exec, but helps if older pidfiles exist)
    if command -v pgrep >/dev/null 2>&1; then
      kids="$(pgrep -P "$pid" || true)"
      if [[ -n "$kids" ]]; then
        echo "[dev_down] killing child processes of $name: $kids"
        kill $kids 2>/dev/null || true
        sleep 1
        kill -9 $kids 2>/dev/null || true
      fi
    fi
  else
    echo "[dev_down] $name not running (pid=$pid)"
  fi

  rm -f "$pid_file"
}

stop_by_pidfile frontend
stop_by_pidfile worker
stop_by_pidfile backend

# Fallback: clean up orphaned processes from previous runs (best-effort)
# Keep patterns narrow to this project.
pkill -f "paperflow-ai/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000" 2>/dev/null || true
pkill -f "Python -m app.workers.worker" 2>/dev/null || true
pkill -f "frontend/node_modules/.bin/vite --host 127.0.0.1 --port 5173" 2>/dev/null || true

echo "[dev_down] done"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
(cd "$ROOT_DIR" && docker compose stop postgres redis qdrant minio grobid r-engine >/dev/null 2>&1 || true)

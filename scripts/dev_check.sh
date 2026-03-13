#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_URL="${PAPERFLOW_HEALTH_URL:-http://127.0.0.1:8000/health}"
FRONTEND_URL="${PAPERFLOW_FRONTEND_URL:-http://127.0.0.1:5173}"
LOG_DIR="$ROOT_DIR/.dev_logs"

echo "[dev_check] checking $HEALTH_URL"

health_json="$(curl -fsS "$HEALTH_URL")"
export PAPERFLOW_HEALTH_JSON="$health_json"
export PAPERFLOW_ALLOW_DOWN_SERVICES="${PAPERFLOW_ALLOW_DOWN_SERVICES:-}"

python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PAPERFLOW_HEALTH_JSON"])
required = payload.get("required_services") or {}
optional = payload.get("optional_services") or {}
allowed_down = {item.strip() for item in os.environ.get("PAPERFLOW_ALLOW_DOWN_SERVICES", "").split(",") if item.strip()}
failed = [name for name, info in required.items() if info.get("status") != "ok" and name not in allowed_down]
expected_storage_backend = os.environ.get("STORAGE_BACKEND", "s3")
reported_storage_backend = ((required.get("storage") or {}).get("backend"))

print("[dev_check] overall_status=", payload.get("overall_status"))
print("[dev_check] required=", ", ".join(f"{name}:{info.get('status')}" for name, info in required.items()))
print("[dev_check] optional=", ", ".join(f"{name}:{info.get('status')}" for name, info in optional.items()))
print("[dev_check] storage_backend=", reported_storage_backend, "(expected:", expected_storage_backend + ")")

if failed:
    print("[dev_check] failing required services:", ", ".join(failed), file=sys.stderr)
    sys.exit(1)
if reported_storage_backend != expected_storage_backend:
    print(
        f"[dev_check] storage backend mismatch: backend reports {reported_storage_backend}, expected {expected_storage_backend}",
        file=sys.stderr,
    )
    sys.exit(1)
PY

check_pid_file() {
  local name="$1"
  local pid_file="$LOG_DIR/${name}.pid"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$pid_file" || true)"
  if [[ -z "$pid" ]]; then
    echo "[dev_check] missing pid for $name" >&2
    return 1
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "[dev_check] process for $name is not alive (pid=$pid)" >&2
    return 1
  fi
  echo "[dev_check] process ok: $name (pid=$pid)"
}

check_pid_file backend
check_pid_file worker-documents
check_pid_file worker-presentations
check_pid_file worker-analysis
check_pid_file frontend

if [[ -f "$LOG_DIR/frontend.pid" ]]; then
  curl -fsS "$FRONTEND_URL" >/dev/null
  echo "[dev_check] frontend reachable at $FRONTEND_URL"
fi

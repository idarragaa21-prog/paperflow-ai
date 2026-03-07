#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEALTH_URL="${PAPERFLOW_HEALTH_URL:-http://127.0.0.1:8000/health}"

echo "[dev_check] checking $HEALTH_URL"

health_json="$(curl -fsS "$HEALTH_URL")"
export PAPERFLOW_HEALTH_JSON="$health_json"

python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PAPERFLOW_HEALTH_JSON"])
required = payload.get("required_services") or {}
optional = payload.get("optional_services") or {}
failed = [name for name, info in required.items() if info.get("status") != "ok"]

print("[dev_check] overall_status=", payload.get("overall_status"))
print("[dev_check] required=", ", ".join(f"{name}:{info.get('status')}" for name, info in required.items()))
print("[dev_check] optional=", ", ".join(f"{name}:{info.get('status')}" for name, info in optional.items()))

if failed:
    print("[dev_check] failing required services:", ", ".join(failed), file=sys.stderr)
    sys.exit(1)
PY

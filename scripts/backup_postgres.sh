#!/usr/bin/env bash
set -euo pipefail

OUT_PATH="${1:-./tmp/backups/postgres/paperflow_$(date +%Y%m%d_%H%M%S).sql}"
mkdir -p "$(dirname "$OUT_PATH")"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-paperflow_ai}" >"$OUT_PATH"
echo "Postgres backup written to $OUT_PATH"

#!/usr/bin/env bash
set -euo pipefail

DUMP_PATH="${1:?usage: ./scripts/restore_postgres.sh path/to/dump.sql}"

docker compose exec -T postgres psql -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-paperflow_ai}" <"$DUMP_PATH"
echo "Postgres restore completed from $DUMP_PATH"

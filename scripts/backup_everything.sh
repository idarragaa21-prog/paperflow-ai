#!/usr/bin/env bash
# ============================================================================
# PaperFlow AI — backup everything
# ----------------------------------------------------------------------------
# Creates a single dated archive containing:
#   • Postgres dump (`pg_dump`)
#   • MinIO bucket mirror (artifacts/PDFs)
#   • PaperFlowAIData directory (local artifacts: matrices, exports, R outputs)
#   • Active .env files (without secrets dump if --redact is passed)
#
# Usage:
#   ./scripts/backup_everything.sh                          # default ./tmp/backups
#   ./scripts/backup_everything.sh /path/to/external/disk   # custom destination
#   ./scripts/backup_everything.sh --redact                 # strip secrets in env
#
# Designed for the single-user local deployment described in CLAUDE.md.
# ============================================================================

set -euo pipefail

REDACT=0
DEST=""
for arg in "$@"; do
  case "$arg" in
    --redact) REDACT=1 ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0 ;;
    *) DEST="$arg" ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

DATA_DIR="${PAPERFLOW_DATA_DIR:-$HOME/PaperFlowAIData}"
TS="$(date +%Y%m%d_%H%M%S)"
DEST="${DEST:-$REPO_ROOT/tmp/backups/full}"
WORK="$DEST/paperflow_backup_$TS"
ARCHIVE="$DEST/paperflow_backup_$TS.tar.gz"

mkdir -p "$WORK/postgres" "$WORK/minio" "$WORK/data" "$WORK/env"

color() { printf "\033[1;36m%s\033[0m\n" "$1"; }
warn()  { printf "\033[1;33m[warn]\033[0m %s\n" "$1"; }
ok()    { printf "\033[1;32m[ok]\033[0m %s\n" "$1"; }

color "→ Postgres dump"
if docker compose ps postgres 2>/dev/null | grep -q "Up"; then
  docker compose exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-paperflow_ai}" \
    > "$WORK/postgres/paperflow_ai.sql"
  ok "postgres → paperflow_ai.sql ($(du -h "$WORK/postgres/paperflow_ai.sql" | cut -f1))"
else
  warn "postgres container is not Up — skipping pg_dump"
fi

color "→ MinIO mirror"
if command -v mc >/dev/null 2>&1; then
  mc alias set paperflow-local \
    "${S3_ENDPOINT_URL:-http://127.0.0.1:9000}" \
    "${MINIO_ROOT_USER:-DEV_ONLY_MINIO_USER}" \
    "${MINIO_ROOT_PASSWORD:-DEV_ONLY_MINIO_PASSWORD}" >/dev/null 2>&1 || true
  if mc ls "paperflow-local/${S3_BUCKET:-paperflow-artifacts}" >/dev/null 2>&1; then
    mc mirror --quiet --overwrite \
      "paperflow-local/${S3_BUCKET:-paperflow-artifacts}" \
      "$WORK/minio/${S3_BUCKET:-paperflow-artifacts}"
    ok "minio bucket mirrored"
  else
    warn "minio bucket not reachable — skipping"
  fi
else
  warn "mc (MinIO client) not installed — skipping bucket mirror"
fi

color "→ Local data directory ($DATA_DIR)"
if [ -d "$DATA_DIR" ]; then
  rsync -a --info=progress2 \
    --exclude '*.tmp' --exclude '__pycache__' --exclude '*.lock' \
    "$DATA_DIR/" "$WORK/data/PaperFlowAIData/"
  ok "data dir → $WORK/data/PaperFlowAIData ($(du -sh "$WORK/data" | cut -f1))"
else
  warn "PaperFlowAIData not found at $DATA_DIR — skipping"
fi

color "→ env files"
for env_file in .env backend/.env frontend/.env; do
  if [ -f "$REPO_ROOT/$env_file" ]; then
    out="$WORK/env/$(echo "$env_file" | tr '/' '__')"
    if [ "$REDACT" -eq 1 ]; then
      sed -E 's/(SECRET|PASSWORD|API_KEY|TOKEN)=.*/\1=__REDACTED__/g' \
        "$REPO_ROOT/$env_file" > "$out"
      ok "redacted env: $env_file"
    else
      cp "$REPO_ROOT/$env_file" "$out"
      ok "copied env: $env_file"
    fi
  fi
done

color "→ Manifest"
{
  echo "PaperFlow AI backup"
  echo "Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Repo: $(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "Branch: $(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  echo "Data dir: $DATA_DIR"
  echo "Redacted env: $REDACT"
  echo
  echo "Contents:"
  (cd "$WORK" && find . -maxdepth 3 -type f | sort)
} > "$WORK/MANIFEST.txt"

color "→ Compressing → $ARCHIVE"
tar -C "$DEST" -czf "$ARCHIVE" "paperflow_backup_$TS"
SIZE=$(du -h "$ARCHIVE" | cut -f1)
rm -rf "$WORK"

ok "Backup complete: $ARCHIVE ($SIZE)"
echo
echo "To restore manually:"
echo "  tar -xzf $ARCHIVE -C /tmp"
echo "  ./scripts/restore_postgres.sh /tmp/paperflow_backup_$TS/postgres/paperflow_ai.sql"
echo "  ./scripts/restore_minio.sh    /tmp/paperflow_backup_$TS/minio/${S3_BUCKET:-paperflow-artifacts}"

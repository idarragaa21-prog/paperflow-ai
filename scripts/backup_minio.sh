#!/usr/bin/env bash
set -euo pipefail

command -v mc >/dev/null 2>&1 || { echo "mc (MinIO client) is required on PATH"; exit 1; }

OUT_DIR="${1:-./tmp/backups/minio}"
mkdir -p "$OUT_DIR"

mc alias set paperflow-local "${S3_ENDPOINT_URL:-http://127.0.0.1:9000}" "${MINIO_ROOT_USER:-DEV_ONLY_MINIO_USER}" "${MINIO_ROOT_PASSWORD:-DEV_ONLY_MINIO_PASSWORD}" >/dev/null
mc mirror "paperflow-local/${S3_BUCKET:-paperflow-artifacts}" "$OUT_DIR"
echo "MinIO backup mirrored to $OUT_DIR"

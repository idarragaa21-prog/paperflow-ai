#!/usr/bin/env bash
set -euo pipefail

command -v mc >/dev/null 2>&1 || { echo "mc (MinIO client) is required on PATH"; exit 1; }

SRC_DIR="${1:?usage: ./scripts/restore_minio.sh path/to/minio-backup-dir}"

mc alias set paperflow-local "${S3_ENDPOINT_URL:-http://127.0.0.1:9000}" "${MINIO_ROOT_USER:-DEV_ONLY_MINIO_USER}" "${MINIO_ROOT_PASSWORD:-DEV_ONLY_MINIO_PASSWORD}" >/dev/null
mc mirror --overwrite "$SRC_DIR" "paperflow-local/${S3_BUCKET:-paperflow-artifacts}"
echo "MinIO restore completed from $SRC_DIR"

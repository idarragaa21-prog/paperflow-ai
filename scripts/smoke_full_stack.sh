#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
docker compose up -d postgres redis qdrant ollama minio minio-init grobid r-engine

"$ROOT_DIR/scripts/dev_check.sh"

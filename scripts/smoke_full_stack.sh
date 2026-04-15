#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PAPERFLOW_SKIP_GROBID_WAIT="${PAPERFLOW_SKIP_GROBID_WAIT:-1}" "$ROOT_DIR/scripts/dev_up.sh"
"$ROOT_DIR/scripts/check_local_ai.sh"
"$ROOT_DIR/scripts/dev_check.sh"

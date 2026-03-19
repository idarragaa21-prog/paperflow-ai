#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.dev_logs"

UID_NUM="$(id -u)"
LA_DIR="$HOME/Library/LaunchAgents"

labels=(
  "ai.paperflow.backend"
  "ai.paperflow.worker"
  "ai.paperflow.frontend"
)

for label in "${labels[@]}"; do
  plist_path="$LA_DIR/${label}.plist"
  if [[ -f "$plist_path" ]]; then
    launchctl bootout "gui/${UID_NUM}" "$plist_path" >/dev/null 2>&1 || true
    rm -f "$plist_path"
    echo "[launchctl] removed: $label"
  else
    echo "[launchctl] missing: $label"
  fi

done

echo "[launchctl] logs in: $LOG_DIR"

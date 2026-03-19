#!/usr/bin/env bash
set -euo pipefail

# Install persistent dev services (backend + worker + frontend) as LaunchAgents.
# This avoids tool-session SIGKILL issues that can kill nohup'd processes.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/.dev_logs"
mkdir -p "$LOG_DIR"

UID_NUM="$(id -u)"
LA_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LA_DIR"

install_plist() {
  local label="$1"; shift
  local plist_path="$LA_DIR/${label}.plist"
  cat >"$plist_path" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-lc</string>
    <string>$*</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${LOG_DIR}/${label}.out.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/${label}.err.log</string>
  <key>WorkingDirectory</key><string>${ROOT_DIR}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
</dict>
</plist>
PLIST

  # Unload if already loaded
  launchctl bootout "gui/${UID_NUM}" "$plist_path" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/${UID_NUM}" "$plist_path"
  launchctl enable "gui/${UID_NUM}/${label}" >/dev/null 2>&1 || true
  launchctl kickstart -k "gui/${UID_NUM}/${label}" >/dev/null 2>&1 || true

  echo "[launchctl] installed: $label"
}

install_plist "ai.paperflow.backend" \
  "cd '$BACKEND_DIR' && source .venv/bin/activate && export PYTHONPATH=. && exec uvicorn app.main:app --host 127.0.0.1 --port 8000"

install_plist "ai.paperflow.worker" \
  "cd '$BACKEND_DIR' && source .venv/bin/activate && export PYTHONPATH=. && exec python -m app.workers.worker"

install_plist "ai.paperflow.frontend" \
  "cd '$FRONTEND_DIR' && exec npm run dev -- --host 127.0.0.1 --port 5173"

echo "[launchctl] done. URLs:"
echo "  backend:  http://127.0.0.1:8000"
echo "  frontend: http://127.0.0.1:5173"

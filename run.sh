#!/usr/bin/env bash
# One-command start: create a venv if needed, install deps, launch the server.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "Creating virtual environment…"
  python3 -m venv .venv
  .venv/bin/pip install -U pip >/dev/null
  .venv/bin/pip install -r requirements.txt
fi

echo "MetaForge running at http://127.0.0.1:8000  (Ctrl-C to stop)"
exec .venv/bin/python -m uvicorn metaforge.api:app --host 127.0.0.1 --port 8000

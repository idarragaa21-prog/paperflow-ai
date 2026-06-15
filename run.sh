#!/usr/bin/env bash
# One-command start (macOS / Linux): set up a venv, install deps, open the app.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "✗ Necesitas Python 3.10 o superior (no se encontró '$PY')."
  echo "  En Mac:  brew install python   (o https://www.python.org/downloads/)"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "▸ Creando entorno virtual…"
  "$PY" -m venv .venv
fi

# Idempotent: fast when already satisfied, and repairs a half-broken install.
echo "▸ Instalando dependencias (sólo la primera vez tarda)…"
.venv/bin/python -m pip install -q --upgrade pip >/dev/null 2>&1 || true
.venv/bin/python -m pip install -q -r requirements.txt

# Sanity check so we fail loudly instead of "barely running".
if ! .venv/bin/python -c "import metaforge.api" >/dev/null 2>&1; then
  echo "✗ La instalación quedó incompleta. Reintenta:  rm -rf .venv && ./run.sh"
  exit 1
fi

URL="http://127.0.0.1:8000"
# Open the browser once the server answers (background).
(
  for _ in $(seq 1 120); do
    curl -fsS "$URL/health" >/dev/null 2>&1 && break
    sleep 0.5
  done
  case "$(uname)" in
    Darwin) open "$URL" >/dev/null 2>&1 || true ;;
    Linux)  xdg-open "$URL" >/dev/null 2>&1 || true ;;
  esac
) &

echo ""
echo "  ⬡  MetaForge → $URL   (Ctrl-C para detener)"
echo ""
exec .venv/bin/python -m uvicorn metaforge.api:app --host 127.0.0.1 --port 8000 --no-access-log

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_ENV_FILE="${PAPERFLOW_BACKEND_ENV_FILE:-$ROOT_DIR/backend/.env}"

ollama_url="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
openclaw_url="${OPENCLAW_BASE_URL:-http://127.0.0.1:18789}"

read_env_value() {
  local key="$1"
  if [[ ! -f "$BACKEND_ENV_FILE" ]]; then
    return 0
  fi
  awk -F= -v key="$key" '
    $1 ~ /^[[:space:]]*#/ {next}
    $1 == key {val=$2; gsub(/^[[:space:]]+|[[:space:]]+$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); print val}
  ' "$BACKEND_ENV_FILE" | tail -n 1
}

chat_model="${PAPERFLOW_CHAT_MODEL:-$(read_env_value PAPERFLOW_CHAT_MODEL)}"
embed_model="${PAPERFLOW_EMBEDDING_MODEL:-$(read_env_value PAPERFLOW_EMBEDDING_MODEL)}"
writing_model="${PAPERFLOW_WRITING_MODEL:-$(read_env_value PAPERFLOW_WRITING_MODEL)}"
vision_model="${PAPERFLOW_VISION_MODEL:-$(read_env_value PAPERFLOW_VISION_MODEL)}"
chat_model="${chat_model:-qwen2.5-coder:7b}"
embed_model="${embed_model:-nomic-embed-text:latest}"
writing_model="${writing_model:-$chat_model}"
vision_model="${vision_model:-qwen3-vl:8b}"

echo "[check_local_ai] expected chat model:    $chat_model"
echo "[check_local_ai] expected writing model: $writing_model"
echo "[check_local_ai] expected vision model:  $vision_model"
echo "[check_local_ai] expected embedding model: $embed_model"

if command -v openclaw >/dev/null 2>&1; then
  echo "[check_local_ai] openclaw binary: $(command -v openclaw)"
  openclaw --version || true
else
  echo "[check_local_ai] ERROR: openclaw binary not found" >&2
fi

if command -v ollama >/dev/null 2>&1; then
  echo "[check_local_ai] ollama binary: $(command -v ollama)"
  ollama --version || true
else
  echo "[check_local_ai] ERROR: ollama binary not found" >&2
fi

openclaw_health="$(curl -fsS "$openclaw_url/health" 2>/dev/null || true)"
if [[ -z "$openclaw_health" ]]; then
  echo "[check_local_ai] ERROR: OpenClaw health check failed at $openclaw_url/health" >&2
  exit 1
fi
echo "[check_local_ai] OpenClaw health: $openclaw_health"

ollama_tags="$(curl -fsS "$ollama_url/api/tags" 2>/dev/null || true)"
if [[ -z "$ollama_tags" ]]; then
  echo "[check_local_ai] ERROR: Ollama tags endpoint failed at $ollama_url/api/tags" >&2
  exit 1
fi

export PAPERFLOW_OLLAMA_TAGS="$ollama_tags"
export PAPERFLOW_CHAT_MODEL="$chat_model"
export PAPERFLOW_WRITING_MODEL="$writing_model"
export PAPERFLOW_VISION_MODEL="$vision_model"
export PAPERFLOW_EMBEDDING_MODEL="$embed_model"

python3 - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["PAPERFLOW_OLLAMA_TAGS"])
chat = os.environ["PAPERFLOW_CHAT_MODEL"]
writing = os.environ["PAPERFLOW_WRITING_MODEL"]
vision = os.environ["PAPERFLOW_VISION_MODEL"]
embed = os.environ["PAPERFLOW_EMBEDDING_MODEL"]

models = [str((item or {}).get("name") or "").strip() for item in (payload.get("models") or [])]
models = [m for m in models if m]

print("[check_local_ai] Ollama models:")
for model in models:
    print(f"  - {model}")

missing = [name for name in [chat, writing, vision, embed] if name not in models]
if missing:
    print("[check_local_ai] ERROR: missing expected Ollama models:", ", ".join(missing), file=sys.stderr)
    sys.exit(1)

print("[check_local_ai] OK: required local AI models are available.")
PY

echo "[check_local_ai] Local AI stack is healthy (OpenClaw + Ollama)."

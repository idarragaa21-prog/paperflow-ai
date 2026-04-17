#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║   PaperFlow AI — Setup inicial para PC personal         ║
# ║   Verifica dependencias, configura .env y descarga       ║
# ║   los modelos Ollama necesarios.                         ║
# ╚══════════════════════════════════════════════════════════╝
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[\u2713]${NC} $1"; }
info() { echo -e "${CYAN}[\u2192]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
die()  { echo -e "${RED}[\u2717]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557${NC}"
echo -e "${CYAN}\u2551     PaperFlow AI \u2014 Setup personal     \u2551${NC}"
echo -e "${CYAN}\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d${NC}"
echo ""

# ── 1. Dependencias del sistema ────────────────────────────
info "Verificando Docker..."
command -v docker >/dev/null 2>&1 || die "Docker no encontrado. Instala Docker Desktop o Docker Engine."
docker info >/dev/null 2>&1 || die "Docker no est\u00e1 corriendo. Arranca Docker primero."
log "Docker OK"

info "Verificando Python 3.11..."
if command -v python3.11 >/dev/null 2>&1; then
  log "Python 3.11 OK"
else
  warn "python3.11 no encontrado. Considera instalarlo:"
  echo "    macOS:  brew install python@3.11"
  echo "    Ubuntu: sudo apt install python3.11 python3.11-venv"
  echo "    pyenv:  pyenv install 3.11.10 && pyenv local 3.11.10"
  read -p "Continuar de todas formas? [y/N] " yn
  [[ "$yn" =~ ^[Yy] ]] || die "Aborta. Instala Python 3.11 primero."
fi

info "Verificando Node \u226520..."
if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -v | sed 's/v\([0-9]*\)\..*/\1/')"
  if [ "${NODE_MAJOR:-0}" -ge 20 ]; then
    log "Node $(node -v) OK"
  else
    die "Node $(node -v) es demasiado viejo. Requiere \u226520."
  fi
else
  die "Node.js no encontrado. Instala Node 20+ desde https://nodejs.org"
fi

# ── 2. Archivos .env ───────────────────────────────────────
info "Configurando archivos .env..."
if [ ! -f "$REPO_DIR/backend/.env" ]; then
  cp "$REPO_DIR/.env.example" "$REPO_DIR/backend/.env"
  log "Creado backend/.env desde .env.example"

  # Generar SECRET_KEY robusto
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  if [ "$(uname)" = "Darwin" ]; then
    sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$REPO_DIR/backend/.env"
  else
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET|" "$REPO_DIR/backend/.env"
  fi
  log "SECRET_KEY generado autom\u00e1ticamente"
else
  warn "backend/.env ya existe \u2014 no se sobreescribe"
fi

if [ ! -f "$REPO_DIR/frontend/.env" ]; then
  if [ -f "$REPO_DIR/frontend/.env.development" ]; then
    cp "$REPO_DIR/frontend/.env.development" "$REPO_DIR/frontend/.env"
  else
    cat > "$REPO_DIR/frontend/.env" <<EOF
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_BASE_PATH=/
EOF
  fi
  log "Creado frontend/.env"
fi

# ── 3. Ollama y modelos ────────────────────────────────────
info "Verificando Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
  warn "Ollama no instalado. Instalando..."
  if [ "$(uname)" = "Darwin" ]; then
    echo "    macOS: descarga Ollama desde https://ollama.ai/download"
    die "Instala Ollama y vuelve a ejecutar este script."
  else
    curl -fsSL https://ollama.ai/install.sh | sh
  fi
fi

# Arrancar Ollama si no est\u00e1 corriendo
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  info "Arrancando servicio Ollama..."
  if [ "$(uname)" = "Darwin" ]; then
    open -a Ollama 2>/dev/null || true
  else
    nohup ollama serve >/tmp/ollama.log 2>&1 &
  fi
  for i in $(seq 1 20); do
    sleep 1
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then break; fi
  done
fi

if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  log "Ollama corriendo en http://127.0.0.1:11434"
else
  warn "Ollama no responde. Arr\u00e1ncalo manualmente: 'ollama serve'"
fi

# Descargar modelos por defecto (los configurados en .env.example)
MODELS=(
  "qwen2.5-coder:7b"
  "nomic-embed-text:latest"
)
# Vision model opcional (3-5 GB)
OPTIONAL_VISION="qwen3-vl:8b"

for MODEL in "${MODELS[@]}"; do
  if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$MODEL"; then
    log "Modelo presente: $MODEL"
  else
    info "Descargando $MODEL (esto puede tardar)..."
    ollama pull "$MODEL" || warn "Fall\u00f3 la descarga de $MODEL (continuando)"
  fi
done

read -p "\u00bfDescargar tambi\u00e9n modelo de visi\u00f3n $OPTIONAL_VISION? (5+ GB) [y/N] " yn
if [[ "$yn" =~ ^[Yy] ]]; then
  ollama pull "$OPTIONAL_VISION" || warn "Fall\u00f3 la descarga"
fi

echo ""
echo -e "${GREEN}\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557${NC}"
echo -e "${GREEN}\u2551       Setup completado                  \u2551${NC}"
echo -e "${GREEN}\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d${NC}"
echo ""
echo "  Siguiente paso: ${CYAN}./start.sh${NC}"
echo ""

#!/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║         PaperFlow AI — Arranque Local               ║
# ╚══════════════════════════════════════════════════════╝

set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"
mkdir -p "$REPO_DIR/logs"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${CYAN}[→]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
die()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        PaperFlow AI  — Local           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Verificar dependencias ──────────────────────────
info "Verificando dependencias..."
command -v docker   >/dev/null 2>&1 || die "Docker no encontrado. Instala Docker Desktop."
command -v python3  >/dev/null 2>&1 || die "Python 3 no encontrado."
command -v node     >/dev/null 2>&1 || die "Node.js no encontrado."
command -v npm      >/dev/null 2>&1 || die "npm no encontrado."
log "Docker, Python, Node OK"

# ── 2. Limpiar contenedores huérfanos ─────────────────
info "Limpiando contenedores huérfanos de arranques anteriores..."
KNOWN_CONTAINERS="paperflow-postgres paperflow-redis paperflow-qdrant paperflow-minio paperflow-minio-init paperflow-grobid paperflow-r-engine"
for c in $KNOWN_CONTAINERS; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${c}$"; then
    docker rm -f "$c" >/dev/null 2>&1 && warn "Removed orphan container: $c" || true
  fi
done
log "Contenedores anteriores limpiados"

# ── 3. Levantar infraestructura Docker ────────────────
info "Levantando servicios Docker (postgres, redis, qdrant, minio, grobid, r-engine)..."
docker compose up -d postgres redis qdrant minio minio-init grobid r-engine

info "Esperando que postgres esté listo..."
for i in $(seq 1 30); do
  if docker exec paperflow-postgres pg_isready -U postgres -d paperflow_ai >/dev/null 2>&1; then
    log "PostgreSQL listo"
    break
  fi
  sleep 2
  if [ $i -eq 30 ]; then die "PostgreSQL no respondió a tiempo."; fi
done

info "Esperando Redis..."
for i in $(seq 1 15); do
  if docker exec paperflow-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    log "Redis listo"
    break
  fi
  sleep 2
  if [ $i -eq 15 ]; then warn "Redis tardando — continuando de todas formas"; fi
done

# ── 4. Backend Python ──────────────────────────────────
info "Configurando entorno Python..."
cd "$REPO_DIR/backend"

# Crear venv si no existe
if [ ! -d ".venv" ]; then
  info "Creando virtualenv..."
  python3.11 -m venv .venv
fi
source .venv/bin/activate

# Instalar dependencias si hay cambios
info "Instalando dependencias Python..."
pip install -r requirements.txt -q

# Migraciones
info "Aplicando migraciones Alembic..."
alembic upgrade head
log "Base de datos actualizada"

# Crear usuario demo si no existe
info "Verificando usuario demo..."
python3 -c "
import asyncio
from app.database import async_session_maker
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

async def run():
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == 'demo@paperflow.ai'))
        if not result.scalars().first():
            user = User(
                email='demo@paperflow.ai',
                full_name='Demo User',
                password_hash=hash_password('demo1234'),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print('  Usuario demo creado: demo@paperflow.ai / demo1234')
        else:
            print('  Usuario demo ya existe')

asyncio.run(run())
"

# Iniciar backend en background
info "Iniciando API backend (puerto 8000)..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > "$REPO_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$REPO_DIR/.backend.pid"

# Iniciar worker RQ en background
info "Iniciando worker RQ..."
nohup python -m app.workers.worker \
  > "$REPO_DIR/logs/worker.log" 2>&1 &
WORKER_PID=$!
echo $WORKER_PID > "$REPO_DIR/.worker.pid"

# Esperar que backend responda
info "Esperando que el backend arranque..."
for i in $(seq 1 20); do
  if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    log "Backend API listo en http://localhost:8000"
    break
  fi
  sleep 2
  if [ $i -eq 20 ]; then warn "Backend tardando — revisa logs/backend.log"; fi
done

deactivate
cd "$REPO_DIR"

# ── 5. Frontend ────────────────────────────────────────
info "Instalando dependencias del frontend..."
cd "$REPO_DIR/frontend"
npm install -q

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ¡Todo listo!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}🌐 App:${NC}      http://localhost:5173"
echo -e "  ${CYAN}🔌 API:${NC}      http://localhost:8000"
echo -e "  ${CYAN}📚 API Docs:${NC} http://localhost:8000/docs"
echo -e "  ${CYAN}📦 MinIO:${NC}    http://localhost:9001"
echo ""
echo -e "  ${CYAN}👤 Login:${NC}    demo@paperflow.ai / demo1234"
echo ""
echo -e "  Logs: ${YELLOW}logs/backend.log${NC}  |  ${YELLOW}logs/worker.log${NC}"
echo -e "  Para parar: ${YELLOW}./stop.sh${NC}"
echo ""

# Iniciar frontend (en foreground para ver los logs)
exec npm run dev

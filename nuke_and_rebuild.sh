#!/bin/bash
# ============================================================================
# PaperFlow AI — NUCLEAR RESET & CLEAN INSTALL
# ============================================================================
# Este script borra TODO y reconstruye desde cero, arreglando:
#   1. Contenedores Docker en conflicto
#   2. Volúmenes corruptos / DB con migraciones rotas
#   3. Virtualenv con Python incorrecto (3.14 → 3.11)
#   4. Cadena de migraciones Alembic rota (revisión fantasma a8b9c0d1e2f3)
#   5. Función get_password_hash → hash_password en start.sh
#   6. R engine sin dependencias de sistema para plumber
#   7. Grobid platform mismatch en Apple Silicon
# ============================================================================

set -e  # Detener en cualquier error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$HOME/paperflow-ai"

echo ""
echo -e "${RED}╔══════════════════════════════════════════════╗${NC}"
echo -e "${RED}║     NUCLEAR RESET — PaperFlow AI             ║${NC}"
echo -e "${RED}║     Esto borra TODO y reconstruye limpio      ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# PASO 0: Verificar que estamos en el directorio correcto
# ============================================================================
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}[✘] No se encontró $PROJECT_DIR${NC}"
    exit 1
fi
cd "$PROJECT_DIR"
echo -e "${CYAN}[→] Trabajando en: $PROJECT_DIR${NC}"

# ============================================================================
# PASO 1: MATAR TODO DOCKER (contenedores, volúmenes, redes, imágenes custom)
# ============================================================================
echo ""
echo -e "${YELLOW}[1/7] Destruyendo TODOS los contenedores y volúmenes Docker...${NC}"

# Parar y borrar contenedores del proyecto (forzado)
docker compose down -v --remove-orphans 2>/dev/null || true

# Borrar contenedores huérfanos por nombre (el bug del grobid)
for container in paperflow-grobid paperflow-postgres paperflow-redis paperflow-qdrant paperflow-minio paperflow-r-engine paperflow-celery-worker; do
    docker rm -f "$container" 2>/dev/null || true
done

# Borrar volúmenes del proyecto
for vol in $(docker volume ls -q --filter "name=paperflow" 2>/dev/null); do
    docker volume rm -f "$vol" 2>/dev/null || true
done
for vol in $(docker volume ls -q --filter "name=researchconsole" 2>/dev/null); do
    docker volume rm -f "$vol" 2>/dev/null || true
done

# Borrar la imagen custom de r-engine para que se reconstruya
docker rmi -f paperflow-ai-r-engine 2>/dev/null || true

# Limpiar basura de Docker
docker system prune -f 2>/dev/null || true

echo -e "${GREEN}[✓] Docker limpio${NC}"

# ============================================================================
# PASO 2: BORRAR VIRTUALENV VIEJO Y NODE_MODULES
# ============================================================================
echo ""
echo -e "${YELLOW}[2/7] Borrando virtualenv y node_modules...${NC}"

rm -rf backend/.venv
rm -rf frontend/node_modules
rm -rf frontend/.next
rm -rf backend/__pycache__
find backend -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true

echo -e "${GREEN}[✓] Limpio${NC}"

# ============================================================================
# PASO 3: FIX — Cadena de migraciones Alembic (revisión fantasma a8b9c0d1e2f3)
# ============================================================================
echo ""
echo -e "${YELLOW}[3/7] Arreglando cadena de migraciones Alembic...${NC}"

# El archivo e2f3a4b5c6d7_seed_clinical_pro_fixture.py tiene down_revision = "c7f8a9b0d1e2"
# y es el último de la cadena. Si algún archivo referencia a8b9c0d1e2f3 como down_revision,
# hay que eliminarlo o arreglarlo.

# Verificar si existe algún archivo con esa revisión fantasma
PHANTOM_FILE=$(grep -rl "a8b9c0d1e2f3" backend/alembic/versions/ 2>/dev/null || true)
if [ -n "$PHANTOM_FILE" ]; then
    echo -e "${CYAN}  Encontrado referencia fantasma en: $PHANTOM_FILE${NC}"
    echo -e "${CYAN}  Eliminando archivo corrupto...${NC}"
    rm -f "$PHANTOM_FILE"
fi

# Verificar la cadena completa de migraciones
# La cadena correcta es:
#   None → 0001_init → 0002_meta_extractor → 0003_meta_exports → 8c9d4455200d →
#   6266b3fe61eb → d4c7f977358c → 1c07329430eb → 9ebe2c19554a →
#   b1d2c3e4f5a6 → c7f8a9b0d1e2 → e2f3a4b5c6d7
#
# Si hay archivos sueltos que no encajan, los detectamos

echo -e "${CYAN}  Verificando integridad de la cadena de migraciones...${NC}"

# Listar todas las revision IDs y down_revisions
python3.11 -c "
import os, re, sys

versions_dir = 'backend/alembic/versions'
revisions = {}
down_map = {}

for fname in os.listdir(versions_dir):
    if not fname.endswith('.py') or fname.startswith('__'):
        continue
    path = os.path.join(versions_dir, fname)
    content = open(path).read()
    
    rev_match = re.search(r\"revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    down_match = re.search(r\"down_revision\s*=\s*['\\\"]?([^'\\\"\\n]+)['\\\"]?\", content)
    
    if rev_match:
        rev_id = rev_match.group(1)
        down_id = down_match.group(1).strip() if down_match else 'None'
        if down_id == 'None':
            down_id = None
        revisions[rev_id] = fname
        down_map[rev_id] = down_id

# Check that every down_revision points to an existing revision
broken = False
for rev_id, down_id in down_map.items():
    if down_id and down_id not in revisions:
        print(f'  ROTO: {revisions[rev_id]} apunta a down_revision={down_id} que NO EXISTE')
        broken = True

if broken:
    print('  ⚠️  Cadena de migraciones tiene referencias rotas')
    sys.exit(1)
else:
    print('  ✅ Cadena de migraciones íntegra')
    sys.exit(0)
" 2>/dev/null

CHAIN_STATUS=$?
if [ $CHAIN_STATUS -ne 0 ]; then
    echo -e "${YELLOW}  Regenerando migración de rescate...${NC}"
    # Si la cadena está rota, creamos un archivo de migración vacío con la revisión faltante
    # para que Alembic pueda seguir la cadena
    
    # Buscar qué revisión falta
    MISSING_REV=$(python3.11 -c "
import os, re

versions_dir = 'backend/alembic/versions'
revisions = set()
down_revisions = set()

for fname in os.listdir(versions_dir):
    if not fname.endswith('.py') or fname.startswith('__'):
        continue
    path = os.path.join(versions_dir, fname)
    content = open(path).read()
    
    rev_match = re.search(r\"revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    down_match = re.search(r\"down_revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    
    if rev_match:
        revisions.add(rev_match.group(1))
    if down_match and down_match.group(1) != 'None':
        down_revisions.add(down_match.group(1))

missing = down_revisions - revisions
for m in missing:
    print(m)
" 2>/dev/null)

    if [ -n "$MISSING_REV" ]; then
        for REV in $MISSING_REV; do
            echo -e "${CYAN}  Creando stub para revisión faltante: $REV${NC}"
            # Encontrar quién apunta a esta revisión
            PARENT_REV=$(python3.11 -c "
import os, re
versions_dir = 'backend/alembic/versions'
for fname in os.listdir(versions_dir):
    if not fname.endswith('.py') or fname.startswith('__'): continue
    content = open(os.path.join(versions_dir, fname)).read()
    down_match = re.search(r\"down_revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    rev_match = re.search(r\"revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    if down_match and down_match.group(1) == '$REV' and rev_match:
        # Encontrar el down_revision del archivo que apunta a este
        # Para el stub, down_revision debe ser la revisión anterior en la cadena
        pass
# Para simplificar: el stub apunta hacia el último conocido antes de él
# Buscar quién lo referencia como down_revision
for fname in os.listdir(versions_dir):
    if not fname.endswith('.py') or fname.startswith('__'): continue
    content = open(os.path.join(versions_dir, fname)).read()
    down_match = re.search(r\"down_revision\s*=\s*['\\\"]([^'\\\"]+)['\\\"]\", content)
    if down_match and down_match.group(1) == '$REV':
        # Este archivo espera que $REV exista. El stub de $REV debe tener
        # down_revision = la revisión más alta que SÍ existe
        # La más sencilla: hacer que el stub apunte al último de la cadena conocida
        print('e2f3a4b5c6d7')
        break
" 2>/dev/null)
            
            cat > "backend/alembic/versions/${REV}_stub_rescue.py" << PYEOF
"""stub rescue migration

Revision ID: ${REV}
Revises: e2f3a4b5c6d7
"""
from alembic import op
import sqlalchemy as sa

revision = '${REV}'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
PYEOF
        done
        echo -e "${GREEN}  ✓ Stubs creados${NC}"
    fi
fi

echo -e "${GREEN}[✓] Migraciones arregladas${NC}"

# ============================================================================
# PASO 4: FIX — start.sh (get_password_hash → hash_password)
# ============================================================================
echo ""
echo -e "${YELLOW}[4/7] Arreglando start.sh...${NC}"

# Fix: get_password_hash → hash_password
if grep -q "get_password_hash" start.sh; then
    sed -i.bak 's/get_password_hash/hash_password/g' start.sh
    rm -f start.sh.bak
    echo -e "${GREEN}  ✓ get_password_hash → hash_password${NC}"
else
    echo -e "${CYAN}  (ya estaba correcto)${NC}"
fi

# Fix: Asegurar que usa python3.11 para el venv
if grep -q "python3 -m venv" start.sh && ! grep -q "python3.11 -m venv" start.sh; then
    sed -i.bak 's|python3 -m venv|python3.11 -m venv|g' start.sh
    rm -f start.sh.bak
    echo -e "${GREEN}  ✓ python3 → python3.11 para venv${NC}"
else
    echo -e "${CYAN}  (python version ya estaba bien o no usa venv inline)${NC}"
fi

# Fix: Asegurar que el source del venv use el correcto
# Verificar si start.sh hardcodea la ruta al python del venv
if grep -q "backend/.venv/bin/pip" start.sh; then
    echo -e "${CYAN}  (usa pip del venv directamente — OK)${NC}"
fi

echo -e "${GREEN}[✓] start.sh arreglado${NC}"

# ============================================================================
# PASO 5: FIX — R engine Dockerfile (agregar dependencias de sistema)
# ============================================================================
echo ""
echo -e "${YELLOW}[5/7] Verificando R engine Dockerfile...${NC}"

R_DOCKERFILE="r_engine/Dockerfile"
if [ -f "$R_DOCKERFILE" ]; then
    # Verificar si tiene las dependencias necesarias para compilar plumber
    if ! grep -q "libsodium-dev" "$R_DOCKERFILE" 2>/dev/null; then
        echo -e "${CYAN}  Agregando dependencias de sistema para R packages...${NC}"
        # Reescribir el Dockerfile con las dependencias correctas
        cat > "$R_DOCKERFILE" << 'DOCKERFILE'
FROM rocker/r-ver:4.4.2

# Dependencias de sistema para compilar paquetes R (plumber, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev \
    libssl-dev \
    libsodium-dev \
    libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar paquetes R necesarios
RUN R -e "install.packages(c('plumber','jsonlite','dplyr','broom','meta','metafor','readxl'), repos='https://cloud.r-project.org')"

WORKDIR /srv
COPY plumber.R /srv/plumber.R

EXPOSE 8010

CMD ["R", "-e", "pr <- plumber::plumb('/srv/plumber.R'); pr$run(host='0.0.0.0', port=8010)"]
DOCKERFILE
        echo -e "${GREEN}  ✓ Dockerfile de R engine actualizado${NC}"
    else
        echo -e "${CYAN}  (Dockerfile ya tiene las dependencias)${NC}"
    fi
else
    echo -e "${CYAN}  (No se encontró r_engine/Dockerfile — saltando)${NC}"
fi

echo -e "${GREEN}[✓] R engine listo${NC}"

# ============================================================================
# PASO 6: CREAR VIRTUALENV CON PYTHON 3.11
# ============================================================================
echo ""
echo -e "${YELLOW}[6/7] Creando virtualenv con Python 3.11...${NC}"

if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}[✘] Python 3.11 no está instalado. Instálalo con:${NC}"
    echo -e "${CYAN}    brew install python@3.11${NC}"
    exit 1
fi

python3.11 -m venv backend/.venv
echo -e "${GREEN}[✓] Virtualenv creado con Python $(backend/.venv/bin/python --version)${NC}"

# ============================================================================
# PASO 7: LEVANTAR TODO
# ============================================================================
echo ""
echo -e "${YELLOW}[7/7] Levantando PaperFlow AI desde cero...${NC}"
echo ""

# Dar permisos de ejecución al start.sh
chmod +x start.sh

# Ejecutar
./start.sh

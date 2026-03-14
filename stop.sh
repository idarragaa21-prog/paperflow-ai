#!/bin/bash
# PaperFlow AI — Para todos los servicios

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}Parando PaperFlow AI...${NC}"

# Backend y worker
for pidfile in .backend.pid .worker.pid; do
  if [ -f "$REPO_DIR/$pidfile" ]; then
    PID=$(cat "$REPO_DIR/$pidfile")
    kill $PID 2>/dev/null && echo -e "${GREEN}[✓]${NC} Proceso $PID parado"
    rm "$REPO_DIR/$pidfile"
  fi
done

# Matar uvicorn y worker por nombre también
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "app.workers.worker" 2>/dev/null || true

# Docker services
echo -e "${CYAN}Parando Docker...${NC}"
cd "$REPO_DIR"
docker compose stop postgres redis qdrant minio grobid r-engine

echo -e "${GREEN}[✓]${NC} Todo parado."

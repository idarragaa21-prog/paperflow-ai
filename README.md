# PaperFlow AI

Web app para flujos de investigación científica:

- búsqueda federada (PubMed/Europe PMC/DOAJ)
- biblioteca de papers y PDFs
- importación y exportación de referencias
- procesamiento documental y trazabilidad de PDFs
- extracción estructurada y exportación
- base local-first para chat con papers y escritura científica

---

## Requisitos

- macOS / Linux
- Python **3.11** (recomendado; evitar 3.14 en macOS por wheels)
- Node **18+**
- Docker runtime (en macOS recomendamos **Colima**)

Opcional (OCR Meta Extractor):
- `tesseract` (`brew install tesseract`)
- `ocrmypdf` (`brew install ocrmypdf`)

---

## Quickstart (Development)

### 0) Docker runtime en macOS (Colima)

```bash
colima start
```

### 1) Infra (Postgres + Redis)

En `PaperFlow AI/`:

```bash
docker compose --env-file .env up -d
```

> Usa `.env.example` como plantilla.

### 2) Backend + Worker + Frontend (recomendado)

Usa los scripts (mantienen PID + logs en `.dev_logs/`):

```bash
./scripts/dev_up.sh
```

URLs:
- Frontend: http://127.0.0.1:5173
- Backend:  http://127.0.0.1:8000

Para bajar todo:

```bash
./scripts/dev_down.sh
```

### 2b) Manual (si prefieres 3 terminales)

Backend (`backend/`):

```bash
cp .env.example .env
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Worker RQ (`backend/`):

```bash
. .venv/bin/activate
python -m app.workers.worker
```

Frontend (`frontend/`):

```bash
cp .env.example .env.local
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

---

## Crear usuario (dev)

En `backend/`:

```bash
. .venv/bin/activate
python scripts/create_user.py --email you@example.com --password 'change-me' --full-name 'Your Name'
```

---

## Troubleshooting (rápido)

### "Connection refused" (curl/Front)
- Asegúrate de que backend/worker/frontend estén arriba (`./scripts/dev_up.sh`).
- Usa `127.0.0.1` (no `localhost`) porque el backend escucha en IPv4 (`--host 127.0.0.1`).

### 401 Unauthorized
- Login no guardó cookies, o estás usando `cookies.txt` distinto.
- Verifica:
  ```bash
  curl -sS -b cookies.txt -w "\nHTTP:%{http_code}\n" http://127.0.0.1:8000/auth/me
  ```

### 403 CSRF token inválido
- Solo aplica a POST/PUT/PATCH/DELETE (mutaciones).
- Debe coincidir cookie `csrf_token` con header `X-CSRF-Token`.

### 429 Too Many Requests (polling)
- Baja el ritmo de polling, o aumenta rate limit en `app/api/jobs.py` (solo dev).

### Worker no procesa jobs
- Redis debe estar arriba (`docker compose up -d`).
- Revisa logs:
  - `.dev_logs/worker.log`

---

## Producción (notas)

- Redis es obligatorio.
- Configurar `SECRET_KEY` fuerte.
- Configurar `OPENCLAW_GATEWAY_TOKEN` si `gateway.auth.mode=token`.
- Ajustar `BACKEND_CORS_ORIGINS` al dominio real.

---

## Scripts

- `scripts/dev_up.sh`: levanta backend + worker + frontend con nohup.
- `scripts/dev_down.sh`: apaga los procesos levantados por `dev_up.sh`.
- `docs/module-map.md`: mapa de transición desde la base legacy a `PaperFlow AI`.

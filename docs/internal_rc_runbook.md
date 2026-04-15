# Internal RC Runbook

## Required services

- `postgres`
- `redis`
- `qdrant`
- `openclaw`
- `ollama`
- `minio`
- `grobid`
- `r-engine`

## Bootstrap

1. Copy `.env.example` and `backend/.env.example`.
2. Create `backend/.venv` with Python 3.11 and install backend requirements.
3. Run `./scripts/dev_up.sh`.
4. Verify `./scripts/dev_check.sh` returns success.

## Release smoke

- Run `./scripts/smoke_full_stack.sh`.
- Confirm `/health` reports `overall_status=ok`.
- Confirm `required_services` are all `ok`.
- Run `cd backend && . .venv/bin/activate && python scripts/run_quality_benchmarks.py`.
- Run `cd backend && . .venv/bin/activate && python scripts/seed_internal_rc_fixture.py`.
- Run `python ./scripts/internal_rc_load.py`.
- Run `cd frontend && npm run e2e`.
- Confirm Prometheus loads `ops/prometheus/alerts.yml` and no runtime alert is firing before release.

## Backup targets

- Postgres database volume
- MinIO bucket `${S3_BUCKET}`

## Failure handling

- If `openclaw`, `ollama`, `grobid`, `qdrant`, `redis`, `minio` or `r-engine` are down, the RC is not releaseable.
- If `prometheus` or `grafana` are down in local dev, the stack may still run, but staging/release smoke should fail.
- Backup and restore procedures are documented in `docs/backup_restore.md`.

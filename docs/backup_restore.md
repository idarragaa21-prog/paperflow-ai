# Backup and Restore

## Postgres

- Backup: `./scripts/backup_postgres.sh`
- Restore: `./scripts/restore_postgres.sh ./tmp/backups/postgres/your_dump.sql`

Both commands operate against the running `postgres` service from `docker compose`.

## MinIO

- Backup: `./scripts/backup_minio.sh`
- Restore: `./scripts/restore_minio.sh ./tmp/backups/minio`

These commands require the `mc` CLI on the host machine and use the current `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` and `S3_BUCKET` values.

## Release checklist

- Take a Postgres backup before destructive migrations.
- Mirror the MinIO bucket before analysis/report migrations.
- Test restore into a disposable stack at least once per release candidate.

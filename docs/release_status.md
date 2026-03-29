# Release Status

## Stable baseline

- `master` is the only supported release baseline.
- GitHub Actions should use Node 24-compatible action versions and Node 24 for frontend/browser jobs.
- CI must stay green for:
  - backend tests
  - frontend lint, unit tests and build
  - browser smoke for auth, search UI and batch traceability
  - local runtime bootstrap (`dev_up` / `dev_check`) before a production push
- Degraded fallbacks in search, analysis and bridged clinical flows must remain explicit through warnings or quality gaps; no silent placeholders in release builds.

## Branch policy

- Divergent feature or audit branches are not merge-ready by default.
- Do not mass-merge stale branches into `master`.
- Reintegrate only by:
  - fresh PR against current `master`, or
  - selective cherry-pick of validated commits

## Final release checks

1. `git fetch --all --prune`
2. `pytest backend/tests -q`
3. `cd frontend && npm run lint && npm run test && npm run build && npm run e2e:smoke`
4. `scripts/dev_down.sh && scripts/dev_up.sh && scripts/dev_check.sh`
5. `cd backend && alembic heads && alembic upgrade head`

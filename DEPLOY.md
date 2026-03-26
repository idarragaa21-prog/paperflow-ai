# Production Deploy

PaperFlow is configured for a split production deploy:

- frontend on Vercel
- backend + workers on Render

This is the default and supported production strategy for this repo.

## Frontend

Set these Vercel environment variables:

- `VITE_API_BASE_URL=https://<your-backend-origin>`
- `VITE_USE_SAME_ORIGIN_API=false`

`VITE_API_BASE_URL` is mandatory in production for the default deploy.
`same-origin` is only supported if you deploy a real reverse proxy that preserves `/api/*`.
The current `vercel.json` intentionally avoids rewriting `/api/*` to `index.html`.

## Backend

Use [render.yaml](/Users/diegoalejandroidarragalopez/Documents/New%20project/render.yaml) as the Render blueprint.

Required environment variables:

- `BACKEND_CORS_ORIGINS=https://<your-vercel-frontend-origin>`
- `COOKIE_DOMAIN` only if you intentionally want cookies shared across subdomains
- database / redis / qdrant / s3 / minio / ollama credentials for your environment

The default Render blueprint sets `COOKIE_SAMESITE=none` because Vercel and Render are split origins and auth cookies must be sent cross-site over HTTPS.
`BACKEND_CORS_ORIGINS` must include the final frontend origin. Leaving it on local defaults will make production CORS fail even if the API is otherwise healthy.

## Strategy

- Production default is separate frontend/backend origins
- `VITE_API_BASE_URL` must be explicit in production
- Cookies are host-only by default; do not set `COOKIE_DOMAIN` unless you need cross-subdomain sharing
- `/api/*` must never be rewritten to `index.html`
- Same-origin is opt-in only when a real proxy exists

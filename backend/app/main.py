from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.analysis import router as analysis_router
from app.api.chat import router as chat_router
from app.api.drafts import router as drafts_router
from app.api.jobs import router as jobs_router
from app.api.references import router as references_router
from app.api.search import router as search_router
from app.api.papers import router as papers_router
from app.api.notes import router as notes_router
from app.api.projects import router as projects_router
from app.api.meta import router as meta_router
from app.api.extraction import router as extraction_router
from app.api.screening import router as screening_router
from app.config import settings
from app.core.metrics import CONTENT_TYPE_LATEST, generate_latest
from app.core.telemetry import instrument_fastapi, setup_telemetry
from app.database import async_session_maker
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import limiter
from app.services.jobs import reconcile_stale_jobs
from app.services.runtime_health import collect_runtime_health

app = FastAPI(title="PaperFlow AI")
setup_telemetry()


def _attach_cors_headers(request: Request, response) -> None:
    origin = request.headers.get("origin")
    if origin and origin in settings.BACKEND_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    response = _rate_limit_exceeded_handler(request, exc)
    _attach_cors_headers(request, response)
    return response

# Middleware (orden importa: auth → csrf → rate limit)
app.add_middleware(AuthMiddleware)
app.add_middleware(CSRFMiddleware)

# Rate limiting (SlowAPI)
# En development: si Redis no está, deshabilitamos rate limiting.
from app.core.redis_conn import redis_available

if settings.RATE_LIMIT_ENABLED and redis_available():
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
instrument_fastapi(app)

# Routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(search_router)
app.include_router(papers_router)
app.include_router(chat_router)
app.include_router(extraction_router)
app.include_router(references_router)
app.include_router(drafts_router)
app.include_router(analysis_router)
app.include_router(screening_router)
app.include_router(notes_router)
app.include_router(projects_router)
app.include_router(meta_router)

if settings.LEGACY_MODULES_ENABLED:
    from app.api.books import router as books_router
    from app.api.clinical import router as clinical_router
    from app.api.presentations import router as presentations_router

    app.include_router(presentations_router)
    app.include_router(clinical_router)
    app.include_router(books_router)


@app.on_event("startup")
async def reconcile_jobs_on_startup() -> None:
    async with async_session_maker() as session:
        await reconcile_stale_jobs(session)


@app.get("/health")
async def health() -> dict:
    details = await collect_runtime_health()
    details["app"] = {
        "name": "PaperFlow AI",
        "env": settings.ENV,
        "runtime_mode_default": settings.PROJECT_DEFAULT_RUNTIME_MODE,
        "legacy_modules_enabled": settings.LEGACY_MODULES_ENABLED,
    }
    details["optional_features"] = {
        "rate_limit": not (settings.RATE_LIMIT_ENABLED and redis_available()),
        "ocr": not settings.OCR_ENABLED,
        "grobid": not settings.GROBID_ENABLED,
    }
    return details


@app.get("/metrics")
async def metrics() -> Response:
    if not settings.METRICS_ENABLED:
        return Response(status_code=404)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

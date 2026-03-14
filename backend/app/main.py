from __future__ import annotations

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.analysis import router as analysis_router
from app.api.chat import router as chat_router
from app.api.drafts import router as drafts_router
from app.api.jobs import router as jobs_router
from app.api.presentations import router as presentations_router
from app.api.references import router as references_router
from app.api.search import router as search_router
from app.api.papers import router as papers_router
from app.api.notes import router as notes_router
from app.api.projects import router as projects_router
from app.api.meta import router as meta_router
from app.api.extraction import router as extraction_router
from app.api.screening import router as screening_router
from app.api.clinical import router as clinical_router
from app.api.books import router as books_router
# (private sources removed by scope change)
from app.config import settings
from app.core.telemetry import instrument_fastapi, setup_telemetry
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import limiter
from app.services.runtime_health import collect_runtime_health

app = FastAPI(title="PaperFlow AI")
setup_telemetry()

# Validate production config on startup (raises RuntimeError if SECRET_KEY is unsafe)
settings.validate_production()

# Middleware (orden importa: auth → csrf → rate limit)
app.add_middleware(AuthMiddleware)
app.add_middleware(CSRFMiddleware)

# Rate limiting (SlowAPI)
# En development: si Redis no está, deshabilitamos rate limiting.
from app.core.redis_conn import redis_available

if settings.RATE_LIMIT_ENABLED and redis_available():
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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
app.include_router(presentations_router)
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
app.include_router(clinical_router)
app.include_router(books_router)
# private_sources_router disabled


@app.get("/health/services")
async def health_services() -> dict:
    from app.services.runtime_health import collect_services_health
    return await collect_services_health()


@app.get("/health")
async def health() -> dict:
    details = await collect_runtime_health()
    details["app"] = {
        "name": "PaperFlow AI",
        "env": settings.ENV,
        "runtime_mode_default": settings.PROJECT_DEFAULT_RUNTIME_MODE,
    }
    details["degraded_features"] = {
        "rate_limit": not (settings.RATE_LIMIT_ENABLED and redis_available()),
        "ocr": not settings.OCR_ENABLED,
        "grobid": not settings.GROBID_ENABLED,
    }
    return details

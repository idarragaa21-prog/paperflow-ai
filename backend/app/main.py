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
from app.api.references import router as references_router
from app.api.search import router as search_router
from app.api.papers import router as papers_router
from app.api.notes import router as notes_router
from app.api.projects import router as projects_router
from app.api.meta import router as meta_router
from app.api.meta_runs import router as meta_runs_router
from app.api.extraction import router as extraction_router
from app.api.screening import router as screening_router
from app.api.clinical import router as clinical_router
from app.api.matrix import router as matrix_router
from app.api.datasets import router as datasets_router
from app.api.writing import router as writing_router
from app.api.artifacts import router as artifacts_router
from app.api.research import router as research_router
# (private sources removed by scope change)
from app.config import settings
from app.core.telemetry import instrument_fastapi, setup_telemetry
from app.middleware.auth import AuthMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import limiter
from app.services.runtime_health import collect_runtime_health

app = FastAPI(title="PaperFlow AI")
setup_telemetry()

# Security guard: abort startup in production if SECRET_KEY was never changed.
import sys
from app.core.logger import logger as _startup_logger
if settings.SECRET_KEY == "CHANGE_ME":
    if settings.ENV == "production":
        _startup_logger.error(
            "FATAL: SECRET_KEY is set to the insecure default 'CHANGE_ME'. "
            "Set a strong random value via the SECRET_KEY environment variable before deploying."
        )
        sys.exit(1)
    else:
        _startup_logger.warning(
            "SECRET_KEY is set to the insecure default 'CHANGE_ME'. "
            "This is acceptable for local development but MUST be changed before deploying to production."
        )

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
app.include_router(jobs_router)
app.include_router(search_router)
app.include_router(papers_router)
app.include_router(chat_router)
app.include_router(extraction_router)
app.include_router(matrix_router)
app.include_router(datasets_router)
app.include_router(references_router)
app.include_router(drafts_router)
app.include_router(analysis_router)
app.include_router(screening_router)
app.include_router(notes_router)
app.include_router(projects_router)
app.include_router(meta_router)
app.include_router(meta_runs_router)
app.include_router(clinical_router)
app.include_router(writing_router)
app.include_router(artifacts_router)
app.include_router(research_router)
# private_sources_router disabled


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


@app.get("/health/services")
async def health_services() -> dict:
    """Timed health check per service with latency in ms."""
    import time
    import httpx
    from app.config import settings as cfg

    results: dict[str, dict] = {}

    # Redis
    t0 = time.monotonic()
    results["redis"] = {"status": "ok" if redis_available() else "down", "latency_ms": round((time.monotonic() - t0) * 1000)}

    # Qdrant
    t0 = time.monotonic()
    try:
        from qdrant_client import QdrantClient
        qc = QdrantClient(url=cfg.QDRANT_URL, timeout=2.0)
        qc.get_collections()
        results["qdrant"] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as exc:
        results["qdrant"] = {"status": "down", "latency_ms": round((time.monotonic() - t0) * 1000), "detail": str(exc)[:120]}

    # HTTP services
    async with httpx.AsyncClient(timeout=3.0) as client:
        for label, url in {
            "grobid": f"{cfg.GROBID_URL.rstrip('/')}/api/isalive",
            "ollama": f"{getattr(cfg, 'OLLAMA_BASE_URL', 'http://localhost:11434')}/api/tags",
            "openclaw": f"{getattr(cfg, 'OPENCLAW_BASE_URL', 'http://localhost:8080')}/health",
        }.items():
            t0 = time.monotonic()
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                results[label] = {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
            except Exception as exc:
                results[label] = {"status": "down", "latency_ms": round((time.monotonic() - t0) * 1000), "detail": str(exc)[:120]}

    return {"services": results}

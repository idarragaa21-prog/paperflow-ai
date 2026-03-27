from __future__ import annotations

import httpx

from app.config import settings
from app.core.redis_conn import redis_available
from app.core.storage import storage_manager


async def collect_runtime_health() -> dict:
    required_services: dict[str, dict] = {
        "redis": {"status": "ok" if redis_available() else "down"},
        "storage": {"status": "ok", "backend": settings.STORAGE_BACKEND},
    }
    optional_services: dict[str, dict] = {
        "prometheus": {"status": "ok" if settings.OTEL_ENABLED else "disabled"},
    }

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
        client.get_collections()
        required_services["qdrant"] = {"status": "ok"}
    except Exception as exc:
        required_services["qdrant"] = {"status": "down", "detail": str(exc)}

    if settings.STORAGE_BACKEND == "s3":
        try:
            storage_manager.ensure_bucket()
            required_services["s3"] = {"status": "ok", "bucket": settings.S3_BUCKET}
        except Exception as exc:
            required_services["s3"] = {"status": "down", "detail": str(exc), "bucket": settings.S3_BUCKET}

    async with httpx.AsyncClient(timeout=3.0) as client:
        ollama_models: set[str] = set()
        ollama_status = "ok"
        ollama_detail = ""
        try:
            ready = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            ready.raise_for_status()
            payload = ready.json() or {}
            ollama_models = {str(model.get("name") or "").strip() for model in payload.get("models") or [] if str(model.get("name") or "").strip()}
        except Exception as exc:
            ollama_status = "down"
            ollama_detail = str(exc)

        embedding_model = settings.PAPERFLOW_EMBEDDING_MODEL
        chat_model = settings.PAPERFLOW_CHAT_MODEL
        configured_models = {
            "embedding": {
                "name": embedding_model,
                "available": embedding_model in ollama_models,
            },
            "chat": {
                "name": chat_model,
                "available": chat_model in ollama_models,
            },
        }
        if ollama_status == "ok" and not configured_models["embedding"]["available"]:
            ollama_status = "degraded"
            ollama_detail = f"Missing configured embedding model: {embedding_model}"
        required_services["ollama"] = {
            "status": ollama_status,
            "configured_models": configured_models,
            "detail": ollama_detail or None,
        }

        for label, url in {
            "r_engine": f"{settings.R_ENGINE_URL.rstrip('/')}/health",
            "grobid": f"{settings.GROBID_URL.rstrip('/')}/api/isalive",
        }.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                body = response.text.strip()
                healthy = body.lower() in {"ok", "true"} or label == "r_engine"
                optional_services[label] = {"status": "ok" if healthy else "degraded", "detail": body[:200]}
            except Exception as exc:
                optional_services[label] = {"status": "down", "detail": str(exc)}

    overall = "ok"
    if any(item["status"] in {"down", "degraded"} for item in required_services.values()):
        overall = "degraded"
    return {
        "overall_status": overall,
        "status": overall,
        "required_services": required_services,
        "optional_services": optional_services,
        "services": {**required_services, **optional_services},
    }

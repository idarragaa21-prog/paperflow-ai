from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.core.redis_conn import redis_available
from app.core.storage import storage_manager


def _feature_status(*, enabled: bool, degraded: bool = False, detail: str | None = None) -> dict:
    if degraded:
        status = "degraded"
    else:
        status = "enabled" if enabled else "disabled"
    payload = {"status": status}
    if detail:
        payload["detail"] = detail
    return payload


async def collect_runtime_health() -> dict:
    required_services: dict[str, dict] = {
        "redis": {"status": "ok" if redis_available() else "down"},
        "storage": {"status": "ok", "backend": settings.STORAGE_BACKEND},
    }
    optional_services: dict[str, dict] = {}

    try:
        from qdrant_client import QdrantClient

        client = await asyncio.to_thread(QdrantClient, url=settings.QDRANT_URL, timeout=2.0)
        await asyncio.to_thread(client.get_collections)
        required_services["qdrant"] = {"status": "ok"}
    except Exception as exc:
        required_services["qdrant"] = {"status": "down", "detail": str(exc)}

    if settings.STORAGE_BACKEND == "s3":
        try:
            await asyncio.to_thread(storage_manager.ensure_bucket)
            required_services["s3"] = {"status": "ok", "bucket": settings.S3_BUCKET}
        except Exception as exc:
            required_services["s3"] = {"status": "down", "detail": str(exc), "bucket": settings.S3_BUCKET}

    async with httpx.AsyncClient(timeout=3.0) as client:
        for label, url in {
            "r_engine": f"{settings.R_ENGINE_URL.rstrip('/')}/health",
            "grobid": f"{settings.GROBID_URL.rstrip('/')}/api/isalive",
        }.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                body = response.text.strip()
                healthy = body.lower() in {"ok", "true"} or label == "r_engine"
                required_services[label] = {"status": "ok" if healthy else "down", "detail": body[:200]}
            except Exception as exc:
                required_services[label] = {"status": "down", "detail": str(exc)}

        try:
            response = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            response.raise_for_status()
            required_services["ollama"] = {
                "status": "ok",
                "base_url": settings.OLLAMA_BASE_URL,
                "models": len((response.json() or {}).get("models") or []),
            }
        except Exception as exc:
            required_services["ollama"] = {"status": "down", "detail": str(exc), "base_url": settings.OLLAMA_BASE_URL}

        for label, url in {
            "prometheus": "http://127.0.0.1:9090/-/ready",
            "grafana": "http://127.0.0.1:3001/api/health",
        }.items():
            try:
                response = await client.get(url)
                response.raise_for_status()
                optional_services[label] = {"status": "ok", "detail": response.text.strip()[:200]}
            except Exception as exc:
                optional_services[label] = {"status": "down", "detail": str(exc)}

    overall = "ok"
    if any(item["status"] != "ok" for item in required_services.values()):
        overall = "down"
    elif any(item["status"] != "ok" for item in optional_services.values()):
        overall = "degraded"
    return {
        "status": overall,
        "overall_status": overall,
        "required_services": required_services,
        "optional_services": optional_services,
        "optional_features": {
            "rate_limit": _feature_status(
                enabled=settings.RATE_LIMIT_ENABLED and redis_available(),
                degraded=settings.RATE_LIMIT_ENABLED and not redis_available(),
                detail="Redis requerido para rate limiting" if settings.RATE_LIMIT_ENABLED and not redis_available() else None,
            ),
            "ocr": _feature_status(enabled=settings.OCR_ENABLED),
            "grobid": _feature_status(enabled=settings.GROBID_ENABLED),
        },
    }

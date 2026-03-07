from __future__ import annotations

import httpx

from app.config import settings
from app.core.redis_conn import redis_available
from app.core.storage import storage_manager


async def collect_runtime_health() -> dict:
    services: dict[str, dict] = {
        "redis": {"status": "ok" if redis_available() else "down"},
        "storage": {"status": "ok", "backend": settings.STORAGE_BACKEND},
    }

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
        client.get_collections()
        services["qdrant"] = {"status": "ok"}
    except Exception as exc:
        services["qdrant"] = {"status": "down", "detail": str(exc)}

    if settings.STORAGE_BACKEND == "s3":
        try:
            storage_manager.ensure_bucket()
            services["s3"] = {"status": "ok", "bucket": settings.S3_BUCKET}
        except Exception as exc:
            services["s3"] = {"status": "down", "detail": str(exc), "bucket": settings.S3_BUCKET}

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
                services[label] = {"status": "ok" if healthy else "degraded", "detail": body[:200]}
            except Exception as exc:
                services[label] = {"status": "down", "detail": str(exc)}

    overall = "ok"
    if any(item["status"] == "down" for item in services.values()):
        overall = "degraded"
    return {"status": overall, "services": services}

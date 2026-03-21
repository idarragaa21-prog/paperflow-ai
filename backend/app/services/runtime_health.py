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


def _configured_model_payload(*, name: str, available_models: set[str]) -> dict:
    return {"name": name, "available": name in available_models}


async def collect_runtime_health() -> dict:
    required_services: dict[str, dict] = {
        "redis": {"status": "ok" if redis_available() else "down"},
        "storage": {"status": "ok", "backend": settings.STORAGE_BACKEND},
    }
    optional_services: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.0)) as client:
        async def check_s3() -> tuple[str, dict]:
            if settings.STORAGE_BACKEND != "s3":
                return "s3", {"status": "disabled", "bucket": settings.S3_BUCKET}
            try:
                response = await client.get(settings.S3_ENDPOINT_URL.rstrip("/"), follow_redirects=True)
                status = "ok" if response.status_code < 500 else "down"
                return "s3", {
                    "status": status,
                    "bucket": settings.S3_BUCKET,
                    "endpoint": settings.S3_ENDPOINT_URL,
                    "detail": f"HTTP {response.status_code}",
                }
            except Exception as exc:
                return "s3", {
                    "status": "down",
                    "detail": str(exc),
                    "bucket": settings.S3_BUCKET,
                    "endpoint": settings.S3_ENDPOINT_URL,
                }

        async def check_qdrant() -> tuple[str, dict]:
            try:
                response = await client.get(f"{settings.QDRANT_URL.rstrip('/')}/collections")
                response.raise_for_status()
                payload = response.json() or {}
                collections = (payload.get("result") or {}).get("collections") or []
                return "qdrant", {"status": "ok", "collections": len(collections)}
            except Exception as exc:
                return "qdrant", {"status": "down", "detail": str(exc)}

        async def check_service(label: str, url: str, *, ok_bodies: set[str] | None = None) -> tuple[str, dict]:
            try:
                response = await client.get(url)
                response.raise_for_status()
                body = response.text.strip()
                healthy = ok_bodies is None or body.lower() in ok_bodies
                return label, {"status": "ok" if healthy else "down", "detail": body[:200]}
            except Exception as exc:
                return label, {"status": "down", "detail": str(exc)}

        async def check_ollama() -> tuple[str, dict]:
            try:
                response = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                response.raise_for_status()
                payload = response.json() or {}
                available_models = {
                    model_name
                    for item in payload.get("models") or []
                    for model_name in (item.get("name") or item.get("model"),)
                    if model_name
                }
                configured_models = {
                    "chat": _configured_model_payload(name=settings.PAPERFLOW_CHAT_MODEL, available_models=available_models),
                    "embedding": _configured_model_payload(
                        name=settings.PAPERFLOW_EMBEDDING_MODEL,
                        available_models=available_models,
                    ),
                    "extraction": _configured_model_payload(
                        name=settings.PAPERFLOW_EXTRACTION_MODEL,
                        available_models=available_models,
                    ),
                }
                missing_models = [item["name"] for item in configured_models.values() if not item["available"]]
                payload_out = {
                    "status": "degraded" if missing_models else "ok",
                    "base_url": settings.OLLAMA_BASE_URL,
                    "models": len(available_models),
                    "available_models": sorted(available_models),
                    "configured_models": configured_models,
                }
                if missing_models:
                    payload_out["detail"] = "Missing configured models: " + ", ".join(missing_models)
                return "ollama", payload_out
            except Exception as exc:
                return "ollama", {"status": "down", "detail": str(exc), "base_url": settings.OLLAMA_BASE_URL}

        results = await asyncio.gather(
            check_s3(),
            check_qdrant(),
            check_service("r_engine", f"{settings.R_ENGINE_URL.rstrip('/')}/health"),
            check_service("grobid", f"{settings.GROBID_URL.rstrip('/')}/api/isalive", ok_bodies={"ok", "true"}),
            check_ollama(),
            check_service("prometheus", "http://127.0.0.1:9090/-/ready"),
            check_service("grafana", "http://127.0.0.1:3001/api/health"),
        )

        for label, payload in results:
            if label in {"prometheus", "grafana"}:
                optional_services[label] = payload
            else:
                required_services[label] = payload

    overall = "ok"
    if any(item["status"] == "down" for item in required_services.values()):
        overall = "down"
    elif any(item["status"] == "degraded" for item in required_services.values()):
        overall = "degraded"
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

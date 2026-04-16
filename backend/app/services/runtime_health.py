from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings
from app.core.redis_conn import redis_available
from app.core.storage import storage_manager


def _status_priority(status: str) -> int:
    return {"ok": 0, "disabled": 0, "degraded": 1, "down": 2}.get(status, 2)


def _llm_runtime_view(*, provider_mode: str, openclaw_status: str, ollama_status: str) -> dict[str, Any]:
    if provider_mode == "auto_local":
        if openclaw_status == "ok":
            return {
                "status": "ok" if ollama_status == "ok" else "degraded",
                "active_provider": "openclaw",
                "fallback_provider": "ollama",
                "detail": "Primary route: OpenClaw. Automatic fallback: Ollama.",
            }
        if ollama_status in {"ok", "degraded"}:
            return {
                "status": "degraded",
                "active_provider": "ollama",
                "fallback_provider": None,
                "detail": "OpenClaw unavailable; running in Ollama-only fallback mode.",
            }
        return {
            "status": "down",
            "active_provider": None,
            "fallback_provider": None,
            "detail": "Neither OpenClaw nor Ollama is available.",
        }

    if provider_mode == "openclaw":
        if openclaw_status == "ok":
            return {
                "status": "ok" if ollama_status == "ok" else "degraded",
                "active_provider": "openclaw",
                "fallback_provider": None,
                "detail": "Configured for OpenClaw only.",
            }
        return {
            "status": "down",
            "active_provider": None,
            "fallback_provider": None,
            "detail": "Configured provider OpenClaw is unavailable.",
        }

    if provider_mode == "ollama":
        return {
            "status": "ok" if ollama_status == "ok" else ollama_status,
            "active_provider": "ollama" if ollama_status != "down" else None,
            "fallback_provider": None,
            "detail": "Configured for Ollama only.",
        }

    # direct_claude and any non-local provider route.
    return {
        "status": "ok",
        "active_provider": provider_mode,
        "fallback_provider": "ollama" if ollama_status in {"ok", "degraded"} else None,
        "detail": "Configured for non-local primary provider.",
    }


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

    openclaw_status = "down"
    openclaw_detail = ""
    openclaw_latency_ms = 0

    ollama_status = "ok"
    ollama_detail = ""
    ollama_latency_ms = 0
    ollama_models: set[str] = set()

    async with httpx.AsyncClient(timeout=3.0) as client:
        # OpenClaw probe
        t0 = time.perf_counter()
        try:
            ready = await client.get(f"{settings.OPENCLAW_BASE_URL.rstrip('/')}/health")
            ready.raise_for_status()
            openclaw_latency_ms = int((time.perf_counter() - t0) * 1000)
            payload = ready.json() if "application/json" in (ready.headers.get("content-type") or "") else {}
            if isinstance(payload, dict) and payload.get("ok") is False:
                openclaw_status = "degraded"
                openclaw_detail = str(payload)
            else:
                openclaw_status = "ok"
                openclaw_detail = None
        except Exception as exc:
            openclaw_latency_ms = int((time.perf_counter() - t0) * 1000)
            openclaw_status = "down"
            openclaw_detail = str(exc)

        # Ollama probe + model inventory
        t0 = time.perf_counter()
        try:
            ready = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            ready.raise_for_status()
            ollama_latency_ms = int((time.perf_counter() - t0) * 1000)
            payload = ready.json() or {}
            ollama_models = {str(model.get("name") or "").strip() for model in payload.get("models") or [] if str(model.get("name") or "").strip()}
        except Exception as exc:
            ollama_latency_ms = int((time.perf_counter() - t0) * 1000)
            ollama_status = "down"
            ollama_detail = str(exc)

        embedding_model = settings.PAPERFLOW_EMBEDDING_MODEL
        chat_model = settings.PAPERFLOW_CHAT_MODEL
        extraction_model = settings.PAPERFLOW_EXTRACTION_MODEL
        writing_model = settings.PAPERFLOW_WRITING_MODEL
        vision_model = getattr(settings, "PAPERFLOW_VISION_MODEL", "")
        configured_models = {
            "embedding": {
                "name": embedding_model,
                "available": embedding_model in ollama_models,
            },
            "chat": {
                "name": chat_model,
                "available": chat_model in ollama_models,
            },
            "extraction": {
                "name": extraction_model,
                "available": extraction_model in ollama_models,
            },
            "writing": {
                "name": writing_model,
                "available": writing_model in ollama_models,
            },
            "vision": {
                "name": vision_model,
                "available": bool(vision_model) and vision_model in ollama_models,
            },
        }
        if ollama_status == "ok":
            missing_required_models = [
                payload["name"]
                for key, payload in configured_models.items()
                if key in {"embedding", "chat", "extraction", "writing"} and not payload["available"]
            ]
            if missing_required_models:
                ollama_status = "degraded"
                ollama_detail = "Missing configured Ollama model(s): " + ", ".join(missing_required_models)
            elif vision_model and not configured_models["vision"]["available"]:
                ollama_detail = f"Configured vision model not available: {vision_model}"

        ollama_payload = {
            "status": ollama_status,
            "configured_models": configured_models,
            "available_models": sorted(ollama_models),
            "latency_ms": ollama_latency_ms,
            "detail": ollama_detail or None,
        }
        required_services["ollama"] = ollama_payload

        openclaw_payload = {
            "status": openclaw_status,
            "latency_ms": openclaw_latency_ms,
            "detail": openclaw_detail or None,
            "base_url": settings.OPENCLAW_BASE_URL,
        }
        if settings.LLM_PROVIDER in {"auto_local", "openclaw"}:
            # In local-first modes OpenClaw should be up. If not, keep runtime alive via fallback but mark degraded.
            if openclaw_status == "down" and ollama_status in {"ok", "degraded"}:
                openclaw_payload["status"] = "degraded"
                openclaw_payload["detail"] = "OpenClaw unavailable; system running with Ollama fallback."
            required_services["openclaw"] = openclaw_payload
        else:
            optional_services["openclaw"] = openclaw_payload

        llm_runtime = _llm_runtime_view(
            provider_mode=settings.LLM_PROVIDER,
            openclaw_status=openclaw_payload["status"],
            ollama_status=ollama_status,
        )
        llm_runtime["provider_mode"] = settings.LLM_PROVIDER
        llm_runtime["chat_model"] = settings.PAPERFLOW_CHAT_MODEL
        llm_runtime["writing_model"] = settings.PAPERFLOW_WRITING_MODEL
        llm_runtime["vision_model"] = getattr(settings, "PAPERFLOW_VISION_MODEL", "")
        llm_runtime["embedding_model"] = settings.PAPERFLOW_EMBEDDING_MODEL
        required_services["llm_runtime"] = llm_runtime

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
    required_statuses = [str(item.get("status") or "down") for item in required_services.values()]
    if any(_status_priority(status) > 0 for status in required_statuses):
        overall = "degraded"

    return {
        "overall_status": overall,
        "status": overall,
        "required_services": required_services,
        "optional_services": optional_services,
        "services": {**required_services, **optional_services},
    }

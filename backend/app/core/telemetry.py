from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.core.logger import logger


@lru_cache(maxsize=1)
def setup_telemetry() -> None:
    if not settings.OTEL_ENABLED:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        from app.database import engine

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        HTTPXClientInstrumentor().instrument()

        setup_telemetry.fastapi_instrumentor = FastAPIInstrumentor  # type: ignore[attr-defined]
        logger.info("OpenTelemetry initialized")
    except Exception as exc:
        logger.warning(f"OpenTelemetry disabled after initialization failure: {exc}")


def instrument_fastapi(app) -> None:
    if not settings.OTEL_ENABLED:
        return
    setup_telemetry()
    instrumentor = getattr(setup_telemetry, "fastapi_instrumentor", None)
    if instrumentor is None:
        return
    instrumentor.instrument_app(app)

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass
class ModelRoute:
    task_type: str
    runtime_mode: str
    provider: str
    model: str


def resolve_model(task_type: str, runtime_mode: str) -> ModelRoute:
    provider = "ollama" if runtime_mode != "cloud_enabled" else settings.LLM_PROVIDER
    normalized = task_type.lower().strip()
    if normalized == "extraction":
        model = settings.PAPERFLOW_EXTRACTION_MODEL
    elif normalized == "writing":
        model = settings.PAPERFLOW_WRITING_MODEL
    else:
        model = settings.PAPERFLOW_CHAT_MODEL
    return ModelRoute(task_type=normalized, runtime_mode=runtime_mode, provider=provider, model=model)

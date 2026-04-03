from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.llm.model_registry import ModelRegistry, TaskType
from app.services.llm.provider_adapters import LLMResponse, get_adapter, CompletionRequest
from app.services.llm.provider_adapters import LLMResponse, get_adapter, LLMCompletionRequest


logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    max_calls: int
    window_sec: int


class RateLimiter:
    """Sliding window rate limiter per provider."""

    def __init__(self):
        self.calls: dict[str, list[datetime]] = defaultdict(list)
        self.limits: dict[str, RateLimit] = {
            "groq": RateLimit(28, 60),
            "gemini": RateLimit(13, 60),
            "cerebras": RateLimit(28, 60),
            "deepseek": RateLimit(55, 60),
            "together": RateLimit(55, 60),
            "sambanova": RateLimit(28, 60),
            "openrouter": RateLimit(55, 60),
            "ollama": RateLimit(999, 60),
            "anthropic": RateLimit(50, 60),
            "openai": RateLimit(50, 60),
        }

    def can_call(self, provider: str) -> bool:
        lim = self.limits.get(provider, RateLimit(60, 60))
        now = datetime.now()
        cutoff = now - timedelta(seconds=lim.window_sec)
        self.calls[provider] = [t for t in self.calls[provider] if t > cutoff]
        return len(self.calls[provider]) < lim.max_calls

    def record_call(self, provider: str) -> None:
        self.calls[provider].append(datetime.now())

    def seconds_until_available(self, provider: str) -> float:
        lim = self.limits.get(provider, RateLimit(60, 60))
        now = datetime.now()
        cutoff = now - timedelta(seconds=lim.window_sec)
        recent = [t for t in self.calls[provider] if t > cutoff]
        if len(recent) < lim.max_calls:
            return 0.0
        oldest = min(recent)
        return (oldest + timedelta(seconds=lim.window_sec) - now).total_seconds()


class SmartRouter:
    def __init__(self, registry: ModelRegistry):
        self.registry = registry
        self.rate_limiter = RateLimiter()

    async def route(
        self,
        *,
        prompt: str,
        task: TaskType,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        free_only: bool = True,
        min_quality: int = 85,
        prefer_speed: bool = False,
        max_retries: int = 3,
        model_override: str | None = None,
        timeout_sec: float = 120.0,
    ) -> LLMResponse:
        if model_override:
            model = self.registry.models.get(model_override)
            if not model:
                raise RuntimeError(f"model_override not found: {model_override}")
            adapter = get_adapter(model)
            request = LLMCompletionRequest(
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
            resp = await adapter.complete(request)
            self.registry.record_result(model.id, 90.0, success=True, latency_ms=resp.latency_ms)
            return resp

        candidates = self.registry.get_best_for_task(task, free_only=free_only, min_quality=min_quality, prefer_speed=prefer_speed)
        if not candidates:
            raise RuntimeError(f"No models available for task {task}")

        last_error: Exception | None = None
        tried: list[str] = []

        for model in candidates[: max_retries + 2]:
            provider_name = model.provider.value
            if not self.rate_limiter.can_call(provider_name):
                wait = self.rate_limiter.seconds_until_available(provider_name)
                logger.info(f"Rate limited: {model.id} (wait {wait:.0f}s), skipping")
                continue

            tried.append(model.id)

            try:
                adapter = get_adapter(model)
                self.rate_limiter.record_call(provider_name)
                logger.info(f"Routing {task.value} -> {model.id}")

                request = LLMCompletionRequest(
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )

                resp = await asyncio.wait_for(
                    adapter.complete(request),
                    timeout=timeout_sec,
                )

                self.registry.record_result(model.id, 90.0, success=True, latency_ms=resp.latency_ms)
                return resp
            except asyncio.TimeoutError as e:
                last_error = TimeoutError(f"{model.id} timed out after {timeout_sec:.0f}s")
                self.registry.record_result(model.id, 0.0, success=False)
                logger.warning(f"timeout: {model.id}")
            except Exception as e:
                last_error = e
                self.registry.record_result(model.id, 0.0, success=False)
                logger.warning(f"failed: {model.id}: {e}")

        raise RuntimeError(f"All models failed for {task.value}. Tried: {tried}. Last: {last_error}")

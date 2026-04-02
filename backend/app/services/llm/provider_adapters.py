from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
import os
import time

import httpx

from app.config import settings
from app.services.llm.model_registry import ModelSpec, Provider
from app.services.llm.openclaw import OpenClawProvider


@dataclass
class LLMRequest:
    prompt: str
    system: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    json_mode: bool = False


@dataclass
class LLMResponse:
    text: str
    model_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float = 0.0
    raw_response: Optional[dict] = None


class LLMAdapter(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    async def health_check(self) -> bool: ...


class OllamaAdapter:
    def __init__(self, model_name: str, base_url: str | None = None):
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        t0 = time.time()
        payload: dict = {
            "model": self.model_name,
            "messages": ([{"role": "system", "content": request.system}] if request.system else []) + [{"role": "user", "content": request.prompt}],
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        if request.json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        return LLMResponse(
            text=data["message"]["content"],
            model_id=f"ollama/{self.model_name}",
            input_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
            latency_ms=(time.time() - t0) * 1000,
            raw_response=data,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                models = [m.get("name", "") for m in r.json().get("models", [])]
                return self.model_name in models or any(self.model_name in m for m in models)
        except Exception:
            return False


class OpenAICompatibleAdapter:
    """Adapter for OpenAI-compatible APIs (Groq, Cerebras, Together, DeepSeek, OpenRouter)."""

    def __init__(self, model_name: str, provider: str, base_url: str, api_key_env: str):
        self.model_name = model_name
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = os.getenv(api_key_env, "")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(f"Missing API key env var for provider {self.provider}")

        t0 = time.time()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict = {
            "model": self.model_name,
            "messages": ([{"role": "system", "content": request.system}] if request.system else []) + [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            model_id=f"{self.provider}/{self.model_name}",
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=(time.time() - t0) * 1000,
            raw_response=data,
        )

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.base_url}/models", headers=headers)
                return r.status_code == 200
        except Exception:
            return False


class OpenClawChatAdapter:
    """Adapter that routes ALL vendor models through OpenClaw (centralized secrets)."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.provider = OpenClawProvider()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # NOTE: OpenClaw may or may not support strict JSON response_format.
        # We keep request.json_mode as an intent signal; upstream should still validate.
        t0 = time.time()
        r = await self.provider.chat(
            model=self.model_name or settings.OPENCLAW_MODEL,
            system=request.system or "",
            user=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            retry=2,
        )
        usage = r.get("usage", {}) or {}
        return LLMResponse(
            text=r["content"],
            model_id=r.get("model") or self.model_name,
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=float(r.get("latency_ms") or ((time.time() - t0) * 1000)),
            cost_usd=float(usage.get("cost_usd") or 0.0),
            raw_response=r,
        )

    async def health_check(self) -> bool:
        try:
            # Minimal: attempt a small completion.
            await self.complete(LLMRequest(prompt="ping", system="", max_tokens=8))
            return True
        except Exception:
            return False


class GeminiAdapter:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")

        t0 = time.time()
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"
        payload: dict = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens},
        }
        if request.system:
            payload["systemInstruction"] = {"parts": [{"text": request.system}]}
        if request.json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {}) if isinstance(data, dict) else {}
        return LLMResponse(
            text=text,
            model_id=f"gemini/{self.model_name}",
            input_tokens=int(usage.get("promptTokenCount", 0) or 0),
            output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            latency_ms=(time.time() - t0) * 1000,
            raw_response=data,
        )

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.base_url}/models?key={self.api_key}")
                return r.status_code == 200
        except Exception:
            return False


PROVIDER_CONFIG: dict[Provider, dict[str, str]] = {
    Provider.GROQ: {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    Provider.DEEPSEEK: {"base_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},
    Provider.CEREBRAS: {"base_url": "https://api.cerebras.ai/v1", "api_key_env": "CEREBRAS_API_KEY"},
    Provider.TOGETHER: {"base_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},
    Provider.OPENROUTER: {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY"},
    Provider.SAMBANOVA: {"base_url": "https://api.sambanova.ai/v1", "api_key_env": "SAMBANOVA_API_KEY"},
    # Provider.OPENAI / Provider.ANTHROPIC are handled elsewhere in the app.
}


def get_adapter(model_spec: ModelSpec) -> LLMAdapter:
    """Factory.

    Default behavior (decision A): route vendor models through OpenClaw.

    Direct-provider adapters remain in this module, but are not used by default.
    """

    if model_spec.provider == Provider.OLLAMA:
        # Optional: keep local Ollama direct call (no secrets, fastest).
        return OllamaAdapter(model_spec.api_model_name)

    # Everything else goes through OpenClaw to keep secrets centralized.
    return OpenClawChatAdapter(model_spec.id)

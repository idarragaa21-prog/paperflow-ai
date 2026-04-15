from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.config import settings
from app.services.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM provider that talks directly to a local Ollama server."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.timeout = 120
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int | None = None,
        retry: int = 2,
    ) -> dict[str, Any]:
        """Call Ollama /api/chat and normalize to OpenClaw-compatible response."""
        last_err: Exception | None = None
        target_model = model if model and model != "default" else settings.PAPERFLOW_CHAT_MODEL

        for attempt in range(retry + 1):
            t0 = time.perf_counter()
            try:
                payload: dict[str, Any] = {
                    "model": target_model,
                    "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                }
                resp = await self.client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=timeout or self.timeout,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                resp.raise_for_status()
                data = resp.json() or {}
                msg = (data.get("message") or {}).get("content") or ""
                return {
                    "content": str(msg),
                    "usage": {
                        "prompt_tokens": int(data.get("prompt_eval_count") or 0),
                        "completion_tokens": int(data.get("eval_count") or 0),
                    },
                    "latency_ms": latency_ms,
                    "model": data.get("model") or target_model,
                }
            except Exception as exc:
                last_err = exc
                if attempt < retry:
                    await asyncio.sleep(0.25 * (attempt + 1))

        raise RuntimeError(f"Ollama chat failed for model={target_model}: {last_err}")

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        system = (
            "Eres un médico especialista experto en análisis de literatura científica médica. "
            "Tu tarea es resumir SOLO con base en el texto proporcionado. "
            "Responde EXCLUSIVAMENTE en español. "
            "NO inventes datos (n, eventos, medidas, OR/RR/HR, p-values, CI, etc.). "
            "Si algo no está explícitamente en el texto, escribe 'No reportado'. "
            "No menciones rutas de archivos ni detalles del sistema. "
            "Devuelve Markdown con títulos (##)."
        )

        user = (
            f"Título: {title}\n\n"
            "Instrucciones de formato (obligatorias):\n"
            "- Usa secciones con encabezados '##'.\n"
            "- Secciones mínimas: ## Resumen, ## Diseño y métodos, ## Población, ## Intervención/Comparador, ## Outcomes, ## Resultados (solo números del texto), ## Limitaciones, ## Conclusión clínica.\n"
            "- Si el texto es insuficiente para un resumen médico (por ejemplo, muy corto o sin contenido científico), dilo explícitamente en ## Resumen y detente.\n"
            "\nTexto (fuente única):\n"
            f"{full_text[:15000]}\n"
        )
        if custom_instructions:
            user += f"\nInstrucciones adicionales del usuario: {custom_instructions}\n"

        r = await self.chat(
            model=settings.PAPERFLOW_SUMMARIZATION_MODEL or settings.PAPERFLOW_CHAT_MODEL,
            system=system,
            user=user,
            temperature=0.2,
            max_tokens=3072,
            retry=2,
        )
        usage = r.get("usage", {}) or {}
        return {
            "summary": r.get("content") or "",
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cost_usd": None,
                "latency_ms": r.get("latency_ms"),
            },
            "model": r.get("model"),
        }

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        seen: set[str] = set()
        for p in papers or []:
            doi = (p.get("doi") or "").strip()
            pmid = str(p.get("pmid") or "").strip()
            key = (f"doi:{doi.lower()}" if doi else f"pmid:{pmid}" if pmid else (p.get("title") or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            title = (p.get("title") or "").strip()
            journal = (p.get("journal") or "").strip()
            year = p.get("pub_year")
            tail = []
            if doi:
                tail.append(f"doi:{doi}")
            if pmid:
                tail.append(f"PMID:{pmid}")
            base = ". ".join([x for x in [title, journal] if x]).strip()
            if year:
                base = (base + f". {year}.").strip()
            if tail:
                base = (base + " " + " ".join(tail)).strip()
            if base:
                refs.append(base)

        return refs[:20]

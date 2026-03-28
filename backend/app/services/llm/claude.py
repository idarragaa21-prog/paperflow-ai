from __future__ import annotations

import asyncio
import time
from typing import Any

from anthropic import AsyncAnthropic

from app.config import settings
from app.services.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Direct Anthropic Claude provider (no OpenClaw intermediary).

    Requires ANTHROPIC_API_KEY in settings. Uses identical prompts and
    return contracts as OpenClawProvider so the two are interchangeable
    via the factory.
    """

    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY requerida para Claude directo")
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.temperature = settings.CLAUDE_TEMPERATURE

    async def chat(
        self,
        *,
        model: str | None = None,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
        retry: int = 2,
    ) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(retry + 1):
            try:
                return await self._chat(
                    model=model,
                    system=system,
                    user=user,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            except Exception as exc:
                last_err = exc
                if attempt < retry:
                    await asyncio.sleep(0.25 * (attempt + 1))
        raise RuntimeError(f"Claude chat failed for model={model or self.model}: {last_err}")

    async def _chat(
        self,
        *,
        model: str | None = None,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Call Claude messages API and return a normalised response dict."""
        t0 = time.perf_counter()
        request = self.client.messages.create(
            model=model or self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        msg = await asyncio.wait_for(request, timeout=timeout) if timeout else await request
        latency_ms = int((time.perf_counter() - t0) * 1000)
        content = msg.content[0].text if msg.content else ""
        usage = msg.usage
        return {
            "content": content,
            "usage": {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "cost_usd": None,  # Anthropic SDK doesn't expose cost directly
                "latency_ms": latency_ms,
            },
            "model": msg.model,
        }

    async def summarize_paper(
        self,
        full_text: str,
        title: str,
        custom_instructions: str | None = None,
    ) -> dict[str, Any]:
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
            "- Secciones mínimas: ## Resumen, ## Diseño y métodos, ## Población, "
            "## Intervención/Comparador, ## Outcomes, ## Resultados (solo números del texto), "
            "## Limitaciones, ## Conclusión clínica.\n"
            "- Si el texto es insuficiente para un resumen médico (por ejemplo, muy corto o sin "
            "contenido científico), dilo explícitamente en ## Resumen y detente.\n"
            "\nTexto (fuente única):\n"
            f"{full_text[:15000]}\n"
        )
        if custom_instructions:
            user += f"\nInstrucciones adicionales del usuario: {custom_instructions}\n"

        r = await self.chat(system=system, user=user, temperature=0.2, max_tokens=4096)
        return {
            "summary": r["content"],
            "usage": r["usage"],
            "model": r["model"],
        }

    async def generate_slide_outline(
        self,
        topic: str,
        duration_minutes: int,
        audience: str,
        papers: list[dict[str, Any]] | None = None,
        num_slides: int | None = None,
    ) -> dict[str, Any]:
        system = (
            "Eres un experto en docencia médica y diseño de presentaciones. "
            "Tu salida DEBE ser SOLO JSON válido (sin markdown, sin texto extra). "
            "Objetivo: una presentación 16:9 profesional, NO genérica, con cifras específicas y referencias. "
            "REGLAS: (1) Cada slide de contenido debe incluir 'takeaway' (1 frase) y 'citations' (lista). "
            "(2) No inventes números; si un dato no está en papers, marca 'No reportado'. "
            "(3) Máx 6 bullets por slide, frases cortas, enfoque clínico. "
            "(4) Incluye 1–3 slides de 'Key Evidence' con tabla comparativa cuando aplique. "
            "(5) Incluye slide final de Referencias."
        )
        user_payload = {
            "schema": {
                "title": "string",
                "slides": [
                    {
                        "type": "title|section|content|evidence_table|references",
                        "title": "string",
                        "subtitle": "string?",
                        "bullets": ["string"],
                        "takeaway": "string?",
                        "citations": ["string"],
                        "table": {"headers": ["string"], "rows": [["string"]]},
                        "notes": "string?",
                    }
                ],
            },
            "topic": topic,
            "duration_minutes": duration_minutes,
            "audience": audience,
            "target_slides": int(num_slides) if num_slides else settings.PRESENTATION_SLIDE_TARGET,
            "papers": papers or [],
            "style": {
                "language": "es",
                "tone": "profesional",
                "avoid_generic": True,
                "include_numbers": True,
                "include_citations": True,
            },
        }
        r = await self.chat(system=system, user=str(user_payload), temperature=0.3, max_tokens=4096)
        return {
            "outline": {"title": topic, "raw": r["content"], "slides": []},
            "usage": r["usage"],
            "model": r["model"],
        }

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        """Format references in Vancouver style.

        Uses deterministic local formatting (same as OpenClawProvider) —
        no LLM call needed here since it avoids hallucination risk.
        """
        refs: list[str] = []
        seen: set[str] = set()
        for p in papers or []:
            doi = (p.get("doi") or "").strip()
            pmid = str(p.get("pmid") or "").strip()
            key = (
                f"doi:{doi.lower()}"
                if doi
                else f"pmid:{pmid}"
                if pmid
                else (p.get("title") or "").strip().lower()
            )
            if key in seen:
                continue
            seen.add(key)
            title = (p.get("title") or "").strip()
            journal = (p.get("journal") or "").strip()
            year = p.get("pub_year")

            tail: list[str] = []
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

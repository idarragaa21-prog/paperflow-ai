from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic

from app.config import settings
from app.core.logger import logger
from app.services.llm.base import LLMProvider

if TYPE_CHECKING:
    from app.services.llm.schemas import GenerateOutlineInput

_NOT_IMPLEMENTED_MSG = (
    "direct-Claude mode does not implement this method. "
    "Set LLM_PROVIDER=openclaw in your environment to use the full feature set."
)


class ClaudeProvider(LLMProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY requerida para Claude directo")
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.temperature = settings.CLAUDE_TEMPERATURE

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
            "Secciones mínimas obligatorias (##): Resumen, Diseño y métodos, Población, "
            "Intervención/Comparador, Outcomes, Resultados (solo números del texto), "
            "Limitaciones, Conclusión clínica.\n\n"
            f"Texto:\n{full_text[:15000]}\n"
        )
        if custom_instructions:
            user += f"\nInstrucciones adicionales: {custom_instructions}\n"

        r = await self.chat(
            model=self.model,
            system=system,
            user=user,
            temperature=0.2,
            max_tokens=self.max_tokens,
        )
        usage = r.get("usage", {}) or {}
        return {
            "summary": r["content"],
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cost_usd": None,
                "latency_ms": r.get("latency_ms"),
            },
            "model": r.get("model"),
        }

    async def generate_slide_outline(
        self,
        input_data: GenerateOutlineInput,
    ) -> dict[str, Any]:
        topic = input_data.topic
        duration_minutes = input_data.duration_minutes
        audience = input_data.audience
        papers = input_data.papers
        num_slides = input_data.num_slides

        from app.config import settings as _s
        import json

        system = (
            "Eres un experto en docencia médica y diseño de presentaciones. "
            "Tu salida DEBE ser SOLO JSON válido (sin markdown, sin texto extra). "
            "Objetivo: presentación 16:9 profesional con cifras específicas y referencias. "
            "REGLAS: cada slide de contenido incluye 'takeaway' (1 frase) y 'citations' (lista). "
            "No inventes números; si un dato no está en papers, marca 'No reportado'. "
            "Máx 6 bullets por slide."
        )
        payload = {
            "schema": {
                "title": "string",
                "slides": [{
                    "type": "title|section|content|evidence_table|references",
                    "title": "string", "subtitle": "string?",
                    "bullets": ["string"], "takeaway": "string?",
                    "citations": ["string"],
                    "table": {"headers": ["string"], "rows": [["string"]]},
                    "notes": "string?",
                }],
            },
            "topic": topic,
            "duration_minutes": duration_minutes,
            "audience": audience,
            "target_slides": int(num_slides) if num_slides else getattr(_s, "PRESENTATION_SLIDE_TARGET", 12),
            "papers": papers or [],
            "style": {"language": "es", "tone": "profesional", "avoid_generic": True},
        }
        r = await self.chat(
            model=self.model,
            system=system,
            user=json.dumps(payload, ensure_ascii=False),
            temperature=0.3,
            max_tokens=self.max_tokens,
        )
        usage = r.get("usage", {}) or {}
        return {
            "outline": {"title": topic, "raw": r["content"], "slides": []},
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
        """Direct Anthropic Messages API call.

        Returns dict compatible with OpenClawProvider.chat: content, usage, latency_ms, model.
        """
        import time

        last_err: Exception | None = None
        for attempt in range(retry + 1):
            t0 = time.perf_counter()
            try:
                resp = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    temperature=temperature,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                content = resp.content[0].text if resp.content else ""
                usage = {
                    "prompt_tokens": resp.usage.input_tokens,
                    "completion_tokens": resp.usage.output_tokens,
                }
                return {"content": content, "usage": usage, "latency_ms": latency_ms, "model": resp.model}
            except Exception as exc:
                last_err = exc
                logger.warning(f"[ClaudeProvider] chat attempt {attempt + 1} failed: {exc!r}")
        raise RuntimeError(f"ClaudeProvider.chat failed after {retry + 1} attempts") from last_err

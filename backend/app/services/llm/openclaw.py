from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.config import settings
from app.services.llm.base import LLMProvider

if TYPE_CHECKING:
    from app.services.llm.schemas import GenerateOutlineInput


class OpenClawProvider(LLMProvider):
    """Single-provider adapter that talks to OpenClaw HTTP.

    IMPORTANT: For multi-vendor orchestration, use EnsembleLLMProvider which calls `chat()`
    with model overrides per pass.
    """

    def __init__(self):
        self.base_url = settings.OPENCLAW_BASE_URL.rstrip("/")
        self.timeout = settings.OPENCLAW_TIMEOUT
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
        """OpenAI-compatible chat completion via OpenClaw.

        Returns dict with: content, usage, latency_ms, model
        """

        last_err: Exception | None = None
        for attempt in range(retry + 1):
            t0 = time.perf_counter()
            try:
                headers = {}
                if settings.OPENCLAW_GATEWAY_TOKEN:
                    headers["Authorization"] = f"Bearer {settings.OPENCLAW_GATEWAY_TOKEN}"
                elif settings.ENV == "production":
                    raise RuntimeError("OPENCLAW_GATEWAY_TOKEN requerido en production")

                resp = await self.client.post(
                    f"{self.base_url}/v1/chat/completions",
                    timeout=timeout or self.timeout,
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {}) or {}
                return {
                    "content": content,
                    "usage": usage,
                    "latency_ms": latency_ms,
                    "model": model,
                }
            except httpx.HTTPStatusError as e:
                # Include status + a small body snippet for debuggability.
                status = getattr(e.response, "status_code", None)
                body = ""
                try:
                    body = (e.response.text or "")[:400]
                except Exception:
                    body = ""
                last_err = RuntimeError(f"HTTP {status} {body}".strip())
                if attempt < retry:
                    await asyncio.sleep(0.25 * (attempt + 1))
            except Exception as e:
                # TimeoutError often has empty str(); keep the class name.
                last_err = RuntimeError(f"{type(e).__name__}: {e}")
                if attempt < retry:
                    await asyncio.sleep(0.25 * (attempt + 1))

        raise RuntimeError(f"OpenClaw chat failed for model={model}: {last_err}")

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
            model=settings.OPENCLAW_MODEL,
            system=system,
            user=user,
            temperature=0.2,
            max_tokens=4096,
            retry=2,
        )
        usage = r.get("usage", {}) or {}
        return {
            "summary": r["content"],
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cost_usd": usage.get("cost_usd"),
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

        # Single-model fallback (not ensemble)
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
        user = {
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
                        "table": {"headers": ["string"], "rows": [["string"]]} ,
                        "notes": "string?"
                    }
                ]
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
        r = await self.chat(
            model=settings.OPENCLAW_MODEL,
            system=system,
            user=str(user),
            temperature=0.3,
            max_tokens=4096,
            retry=2,
        )
        # Best-effort: return raw text; caller should validate
        usage = r.get("usage", {}) or {}
        return {
            "outline": {"title": topic, "raw": r["content"], "slides": []},
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "cost_usd": usage.get("cost_usd"),
                "latency_ms": r.get("latency_ms"),
            },
            "model": r.get("model"),
        }

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        # Minimal safe formatter (no invention) - keeps your existing behavior
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

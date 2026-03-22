from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.config import settings
from app.core.logger import logger
from app.schemas.presentation_outline import PresentationOutline, outline_warnings
from app.services.llm.base import LLMProvider
from app.services.llm.openclaw import OpenClawProvider


def _now_ms() -> int:
    return int(time.perf_counter() * 1000)


def _safe_json_loads(text: str) -> Any:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        # try extract first json object
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in model output")
        depth = 0
        end = None
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            raise ValueError("Unterminated JSON object")
        return json.loads(text[start:end])


def _estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    # configurable table (can be refined later). Values are USD per 1M tokens.
    # If unknown → None
    price_table = {
        settings.OPENCLAW_CLAUDE_MODEL: {"in": 15.0, "out": 75.0},
        settings.OPENCLAW_OPENAI_MODEL: {"in": 5.0, "out": 15.0},
        settings.OPENCLAW_GEMINI_MODEL: {"in": 1.0, "out": 3.0},
    }
    if model not in price_table:
        return None
    p = price_table[model]
    return (input_tokens / 1_000_000) * p["in"] + (output_tokens / 1_000_000) * p["out"]


class EnsembleLLMProvider(LLMProvider):
    """Draft → Critique → Revise → Validate.

    - Writer: Claude Sonnet 4.5
    - Critic: OpenAI
    - Validator: Gemini

    Requires OpenClaw routing for multi-vendor.
    """

    def __init__(self, openclaw: OpenClawProvider):
        self.openclaw = openclaw

    async def summarize_paper(self, full_text: str, title: str, custom_instructions: str | None = None) -> dict[str, Any]:
        return await self.openclaw.summarize_paper(full_text, title, custom_instructions)

    async def format_references_vancouver(self, papers: list[dict[str, Any]]) -> list[str]:
        return await self.openclaw.format_references_vancouver(papers)

    async def generate_slide_outline(
        self,
        topic: str,
        duration_minutes: int,
        audience: str,
        papers: list[dict[str, Any]] | None = None,
        num_slides: int | None = None,
    ) -> dict[str, Any]:
        if settings.LLM_PROVIDER != "openclaw":
            raise RuntimeError(
                "LLM_STRATEGY=ensemble requiere LLM_PROVIDER=openclaw (necesita Claude+OpenAI+Gemini)."
            )

        target = int(num_slides) if num_slides else settings.PRESENTATION_SLIDE_TARGET
        target = max(20, min(50, target))

        # Allowed window around target (keep within 20–50)
        min_s = max(20, min(settings.PRESENTATION_SLIDE_MIN, target - 5))
        max_s = min(50, max(settings.PRESENTATION_SLIDE_MAX, target + 5))
        papers = papers or []

        passes: list[dict[str, Any]] = []

        def log(msg: str) -> None:
            logger.debug(msg)

        # PASS 1: DRAFT (Claude)
        system_draft = (
            "Eres un profesor clínico experto. Debes devolver SOLO JSON válido (sin markdown, sin texto extra).\n"
            "No inventes datos. Si algo no está reportado, escribe: 'No reportado en el texto'.\n"
            f"Genera un outline de presentación con target {target} slides (permitido {min_s}–{max_s}).\n"
            "Reglas: 1er slide type=title; último slide type=references.\n"
            "Densidad: ideal 4–6 bullets por slide, máximo 6 recomendado (permitido hasta 10).\n"
            "Debe incluir: 1–2 slides Take-home messages, 1 slide Algorithm/Figure (image_placeholder), "
            "1 slide Limitations/Evidence, y secciones claras." 
        )
        user_draft = json.dumps(
            {
                "topic": topic,
                "duration_minutes": duration_minutes,
                "audience": audience,
                "target_slides": target,
                "min_slides": min_s,
                "max_slides": max_s,
                "papers": papers,
                "output_schema": {
                    "title": "str",
                    "slides": [
                        {"type": "title", "title": "str", "subtitle": "str"},
                        {"type": "section|divider", "title": "str", "notes": "str"},
                        {"type": "content", "title": "str", "content": ["..."], "notes": "str"},
                        {"type": "image_placeholder", "title": "str", "image_suggestion": "str", "notes": "str"},
                        {"type": "references", "title": "Referencias", "notes": "str"},
                    ],
                },
            },
            ensure_ascii=False,
        )

        log(f"[PASS draft] model={settings.OPENCLAW_CLAUDE_MODEL}...")
        p1_t0 = _now_ms()
        r1 = await self.openclaw.chat(
            model=settings.OPENCLAW_CLAUDE_MODEL,
            system=system_draft,
            user=user_draft,
            temperature=0.3,
            max_tokens=4096,
            timeout=settings.OPENCLAW_TIMEOUT,
            retry=2,
        )
        p1_ms = _now_ms() - p1_t0
        draft_text = r1["content"]

        # Parse JSON; if invalid, one repair attempt with Claude
        try:
            draft_json = _safe_json_loads(draft_text)
        except Exception as e:
            system_repair = (
                "Tu salida anterior NO fue JSON válido. Debes devolver SOLO JSON válido, sin markdown, sin comentarios. "
                "Corrige únicamente la sintaxis (comas, llaves, comillas), sin cambiar el contenido clínico."
            )
            user_repair = json.dumps(
                {
                    "error": str(e),
                    "previous_output": draft_text[:20000],
                    "instruction": "Devuelve JSON válido completo del outline.",
                },
                ensure_ascii=False,
            )
            t0 = _now_ms()
            r1b = await self.openclaw.chat(
                model=settings.OPENCLAW_CLAUDE_MODEL,
                system=system_repair,
                user=user_repair,
                temperature=0.0,
                max_tokens=4096,
                timeout=settings.OPENCLAW_TIMEOUT,
                retry=2,
            )
            p1b_ms = _now_ms() - t0
            passes.append(_usage_record("draft_repair", settings.OPENCLAW_CLAUDE_MODEL, r1b, p1b_ms))
            draft_text = r1b["content"]
            draft_json = _safe_json_loads(draft_text)

        passes.append(_usage_record("draft", settings.OPENCLAW_CLAUDE_MODEL, r1, p1_ms))

        # PASS 2: CRITIQUE (OpenAI)
        system_crit = (
            "Eres un crítico de presentaciones médicas. Devuelve SOLO JSON válido.\n"
            "NO reescribas el outline completo. Solo lista issues y fixes sugeridos.\n"
            "Chequea: conteo de slides, title/references, densidad bullets, slides requeridos (take-home, algorithm, limitations), "
            "coherencia clínica, redundancia, y campos vacíos." 
        )
        user_crit = json.dumps(
            {
                "draft": draft_json,
                "rules": {
                    "slide_count": {"min": min_s, "max": max_s, "target": target},
                    "must_have": [
                        "title_first",
                        "references_last",
                        "take_home_1_2",
                        "algorithm_figure_image_placeholder",
                        "limitations_evidence",
                    ],
                    "bullets": {"recommended_max": 6, "allowed_max": 10},
                },
                "output_schema": {
                    "issues": [
                        {
                            "severity": "high|med|low",
                            "path": "str",
                            "problem": "str",
                            "fix": "str",
                        }
                    ],
                    "global_suggestions": ["..."]
                },
            },
            ensure_ascii=False,
        )

        log(f"[PASS critique] model={settings.OPENCLAW_OPENAI_MODEL}...")
        p2_t0 = _now_ms()
        r2 = await self.openclaw.chat(
            model=settings.OPENCLAW_OPENAI_MODEL,
            system=system_crit,
            user=user_crit,
            temperature=0.0,
            max_tokens=2048,
            timeout=settings.OPENCLAW_TIMEOUT,
            retry=2,
        )
        p2_ms = _now_ms() - p2_t0
        critique_json = _safe_json_loads(r2["content"])
        passes.append(_usage_record("critique", settings.OPENCLAW_OPENAI_MODEL, r2, p2_ms))

        # PASS 3: REVISE (Claude)
        system_rev = (
            "Eres el escritor senior (docencia médica). Devuelve SOLO JSON válido del outline COMPLETO revisado.\n"
            "Aplica las correcciones del crítico. NO inventes datos. Si falta info -> 'No reportado en el texto'.\n"
            f"Mantén el conteo de slides en {min_s}–{max_s} (target {target}). "
            "Asegura: title first, references last, take-home, algorithm/figure, limitations/evidence." 
        )
        user_rev = json.dumps(
            {"draft": draft_json, "critique": critique_json, "target": target, "min": min_s, "max": max_s},
            ensure_ascii=False,
        )

        async def _revise_once() -> tuple[dict[str, Any], dict[str, Any], int]:
            t0 = _now_ms()
            rr = await self.openclaw.chat(
                model=settings.OPENCLAW_CLAUDE_MODEL,
                system=system_rev,
                user=user_rev,
                temperature=0.3,
                max_tokens=4096,
                timeout=settings.OPENCLAW_TIMEOUT,
                retry=2,
            )
            ms = _now_ms() - t0
            outline = _safe_json_loads(rr["content"])
            return outline, rr, ms

        log(f"[PASS revise] model={settings.OPENCLAW_CLAUDE_MODEL}...")
        revised_json, r3, p3_ms = await _revise_once()
        passes.append(_usage_record("revise", settings.OPENCLAW_CLAUDE_MODEL, r3, p3_ms))

        # PASS 4: VALIDATE (Gemini)
        system_val = (
            "Eres un validador estricto de outline JSON. Devuelve SOLO JSON válido con el siguiente schema:\n"
            "{verdict:'VALID'|'INVALID', errors:[{path:'...', message:'...'}]}\n"
            "Valida: conteo {min}-{max}, title first, references last, no slides vacíos, content bullets 1..10." 
        ).format(min=min_s, max=max_s)
        user_val = json.dumps({"outline": revised_json}, ensure_ascii=False)

        async def _validate(outline_obj: Any) -> tuple[dict[str, Any], dict[str, Any], int]:
            t0 = _now_ms()
            rr = await self.openclaw.chat(
                model=settings.OPENCLAW_GEMINI_MODEL,
                system=system_val,
                user=json.dumps({"outline": outline_obj}, ensure_ascii=False),
                temperature=0.0,
                max_tokens=1024,
                timeout=settings.OPENCLAW_TIMEOUT,
                retry=2,
            )
            ms = _now_ms() - t0
            verdict = _safe_json_loads(rr["content"])
            return verdict, rr, ms

        log(f"[PASS validate] model={settings.OPENCLAW_GEMINI_MODEL}...")
        verdict_json, r4, p4_ms = await _validate(revised_json)
        passes.append(_usage_record("validate", settings.OPENCLAW_GEMINI_MODEL, r4, p4_ms))

        # If INVALID -> one more revise with Claude using validator errors
        if isinstance(verdict_json, dict) and verdict_json.get("verdict") == "INVALID":
            errors = verdict_json.get("errors") or []
            system_retry = system_rev + "\n\nAdemás, corrige estos errores del validador (sin inventar):"
            user_retry = json.dumps({"outline": revised_json, "validator_errors": errors}, ensure_ascii=False)

            t0 = _now_ms()
            r5 = await self.openclaw.chat(
                model=settings.OPENCLAW_CLAUDE_MODEL,
                system=system_retry,
                user=user_retry,
                temperature=0.3,
                max_tokens=4096,
                timeout=settings.OPENCLAW_TIMEOUT,
                retry=2,
            )
            p5_ms = _now_ms() - t0
            revised_json = _safe_json_loads(r5["content"])
            passes.append(_usage_record("revise_retry", settings.OPENCLAW_CLAUDE_MODEL, r5, p5_ms))

            verdict2, r6, p6_ms = await _validate(revised_json)
            passes.append(_usage_record("validate_retry", settings.OPENCLAW_GEMINI_MODEL, r6, p6_ms))
            if not (isinstance(verdict2, dict) and verdict2.get("verdict") == "VALID"):
                raise ValueError(f"Outline inválido tras retry: {verdict2}")

        # Local Pydantic validation (hard) + warnings
        outline_obj = PresentationOutline.model_validate(revised_json)
        warnings = outline_warnings(outline_obj)

        usage = _aggregate_pass_usage(passes)
        usage["warnings"] = warnings

        return {
            "outline": outline_obj.model_dump(),
            "usage": usage,
            "model": "ensemble",
        }


def _usage_record(pass_name: str, model: str, resp: dict[str, Any], latency_ms: int) -> dict[str, Any]:
    u = resp.get("usage") or {}
    input_tokens = int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
    output_tokens = int(u.get("completion_tokens") or u.get("output_tokens") or 0)
    cost = u.get("cost_usd")
    if cost is None:
        cost = _estimate_cost_usd(model, input_tokens, output_tokens)

    return {
        "name": pass_name,
        "model": model,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }


def _aggregate_pass_usage(passes: list[dict[str, Any]]) -> dict[str, Any]:
    in_total = sum(int(p.get("input_tokens") or 0) for p in passes)
    out_total = sum(int(p.get("output_tokens") or 0) for p in passes)

    # If any cost is None -> total None
    if any(p.get("cost_usd") is None for p in passes):
        total_cost = None
    else:
        total_cost = float(sum(float(p.get("cost_usd") or 0.0) for p in passes))

    return {
        "input_tokens_total": in_total,
        "output_tokens_total": out_total,
        "total_cost_usd": total_cost,
        "passes": passes,
        "models_used": [p.get("model") for p in passes],
    }

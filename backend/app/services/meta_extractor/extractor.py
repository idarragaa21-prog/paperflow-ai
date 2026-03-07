from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.core.logger import logger
from app.services.llm.openclaw import OpenClawProvider
from app.services.meta_extractor.prompts import (
    BASE_SYSTEM_PROMPT,
    CASE_CONTROL_PROMPT,
    COHORT_PROMPT,
    DIAGNOSTIC_PROMPT,
    RCT_PROMPT,
)
from app.services.meta_extractor.schema import ExtractedStudySchema


def _pick_prompt(study_design: str | None) -> str:
    s = (study_design or "").lower()
    if "rct" in s or "random" in s:
        return RCT_PROMPT
    if "cohort" in s:
        return COHORT_PROMPT
    if "case" in s and "control" in s:
        return CASE_CONTROL_PROMPT
    if "diagn" in s:
        return DIAGNOSTIC_PROMPT
    return BASE_SYSTEM_PROMPT


@dataclass
class MetaExtractorInput:
    text: str
    tables_markdown: str
    ocr_snippets: str
    guessed_design: str | None = None


async def _call_llm(system: str, user: str, model: str, retry: int = 2) -> dict[str, Any]:
    oc = OpenClawProvider()
    last_err: Exception | None = None
    for attempt in range(retry + 1):
        try:
            # Meta-extraction can be slower than summaries; give it a longer per-call timeout.
            return await oc.chat(model=model, system=system, user=user, temperature=0.2, max_tokens=4096, timeout=240, retry=0)
        except Exception as e:
            last_err = e
            if attempt < retry:
                sleep_s = 2 ** attempt * 2
                await asyncio.sleep(sleep_s)

    raise RuntimeError(f"LLM extraction failed after retries: {last_err}")


async def extract_study_json(inp: MetaExtractorInput) -> dict[str, Any]:
    system = _pick_prompt(inp.guessed_design)

    user = json.dumps(
        {
            "paper_text": inp.text[:20000],
            "tables_markdown": inp.tables_markdown[:20000],
            "ocr_snippets": inp.ocr_snippets[:20000],
            "schema": "ExtractedStudySchema",
        }
    )

    model = settings.OPENCLAW_CLAUDE_MODEL if settings.LLM_STRATEGY == "ensemble" else settings.OPENCLAW_MODEL

    r = await _call_llm(system=system, user=user, model=model, retry=2)
    content = (r.get("content") or "").strip()

    # parse JSON strictly, but allow wrapper
    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise


async def extract_and_validate(inp: MetaExtractorInput) -> ExtractedStudySchema:
    data = await extract_study_json(inp)
    return ExtractedStudySchema.model_validate(data)

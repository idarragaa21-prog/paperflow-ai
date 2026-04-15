from __future__ import annotations

import json
import os
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.clinical import ClinicalConsult, ClinicalConsultClaim, ClinicalConsultSource
from app.models.paper import Paper
from app.services.llm.factory import llm_provider
from app.services.pubmed import pubmed_client


SUPPORTED_CONSULT_MODES = {"brief", "standard", "deep"}


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if len(token) > 2]


def _score_paper(paper: Paper, query_tokens: list[str]) -> int:
    haystack = " ".join([paper.title or "", paper.abstract_text or "", paper.full_text_extracted or ""]).lower()
    return sum(1 for token in query_tokens if token in haystack)


def _clip(text: str | None, *, max_len: int = 320) -> str:
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "…"


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    text = (raw_text or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _safe_confidence(value: Any, default: float = 0.6) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def _build_claim(source_title: str, excerpt: str) -> str:
    text = _clip(excerpt, max_len=260)
    if not text:
        return ""
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", text) if chunk.strip()]
    if not sentences:
        return text

    # Prefer sentence-level extractive claims with quantified language.
    quantified = [item for item in sentences if re.search(r"\d|%|ci|or|rr|hr|hazard|risk", item, flags=re.I)]
    candidate = quantified[0] if quantified else sentences[0]
    return _clip(candidate, max_len=220)


def _answer_limits(mode: str) -> tuple[int, int]:
    if mode == "brief":
        return 3, 2
    if mode == "deep":
        return 10, 8
    return 6, 4


async def _llm_grounded_consult_payload(
    *,
    question: str,
    mode: str,
    sources: list[ClinicalConsultSource],
    claim_limit: int,
) -> dict[str, Any] | None:
    # Keep tests deterministic and offline-fast.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return None
    if not sources:
        return None

    provider = llm_provider()
    if not hasattr(provider, "chat"):
        return None

    source_lines = []
    for source in sources:
        source_lines.append(
            {
                "source_id": str(source.id),
                "title": source.title,
                "pmid": source.pmid,
                "doi": source.doi,
                "source_kind": source.source_kind,
                "excerpt": _clip(source.excerpt, max_len=340),
            }
        )

    system = (
        "You are a clinical evidence synthesis assistant. "
        "You must ONLY use the provided sources. "
        "Every claim must map to one or more provided source_id values. "
        "No source_id, no factual claim."
    )
    user = (
        f"Clinical question: {question}\n"
        f"Mode: {mode}\n"
        f"Max claims: {claim_limit}\n\n"
        "Available sources (JSON):\n"
        f"{json.dumps(source_lines, ensure_ascii=False)}\n\n"
        "Return STRICT JSON with this schema:\n"
        "{\n"
        '  "actionable_summary": "string",\n'
        '  "uncertainty": "string",\n'
        '  "limitations": "string",\n'
        '  "claims": [\n'
        "    {\n"
        '      "claim_text": "string",\n'
        '      "source_ids": ["source_id_1"],\n'
        '      "support_level": "strong|moderate|limited",\n'
        '      "uncertainty": "string",\n'
        '      "confidence": 0.0\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )
    try:
        response = await provider.chat(  # type: ignore[attr-defined]
            model=settings.PAPERFLOW_WRITING_MODEL,
            system=system,
            user=user,
            temperature=0.1,
            max_tokens=1400,
            timeout=40,
            retry=1,
        )
    except Exception:
        return None

    parsed = _extract_json_object(str(response.get("content") or ""))
    if not parsed:
        return None
    return parsed


async def _collect_project_sources(
    db: AsyncSession,
    *,
    question: str,
    project_id: UUID,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = _tokenize(question)
    q = await db.execute(
        select(Paper)
        .where(Paper.project_id == project_id)
        .order_by(Paper.downloaded_at.desc(), Paper.created_at.desc())
        .limit(80)
    )
    ranked: list[tuple[int, Paper]] = []
    for paper in q.scalars().all():
        ranked.append((_score_paper(paper, tokens), paper))
    ranked.sort(key=lambda item: item[0], reverse=True)

    sources: list[dict[str, Any]] = []
    for score, paper in ranked:
        if score <= 0 and len(sources) >= max(2, limit // 2):
            continue
        excerpt = _clip(paper.abstract_text or paper.full_text_extracted, max_len=380)
        sources.append(
            {
                "source_kind": "project_paper",
                "paper_id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.publication_year,
                "doi": paper.doi,
                "pmid": paper.pmid,
                "url": paper.oa_url,
                "excerpt": excerpt,
                "locator_json": {"paper_id": str(paper.id)},
                "relevance": float(score),
                "confidence": 0.8 if score > 0 else 0.5,
            }
        )
        if len(sources) >= limit:
            break
    return sources


async def _collect_pubmed_sources(
    *,
    question: str,
    limit: int,
) -> list[dict[str, Any]]:
    bundle = await pubmed_client.search_and_fetch(question, max_results=max(limit * 2, 10))
    results = bundle.get("results") or []
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(results[:limit], start=1):
        out.append(
            {
                "source_kind": "pubmed",
                "paper_id": None,
                "title": item.get("title"),
                "authors": ", ".join(item.get("authors") or []),
                "year": item.get("pub_year"),
                "doi": item.get("doi"),
                "pmid": item.get("pmid"),
                "url": item.get("oa_url"),
                "excerpt": _clip(item.get("abstract"), max_len=380),
                "locator_json": {"pmid": item.get("pmid")},
                "relevance": float(max(limit - idx, 1)),
                "confidence": 0.7,
            }
        )
    return out


def _compose_answer(
    *,
    question: str,
    mode: str,
    sources: list[ClinicalConsultSource],
    claims: list[ClinicalConsultClaim],
    actionable_summary: str | None = None,
    uncertainty_override: str | None = None,
    limitations_override: str | None = None,
) -> tuple[str, dict[str, Any], str, str]:
    citation_rows = []
    source_marker: dict[str, str] = {}
    for idx, source in enumerate(sources, start=1):
        marker = f"[{idx}]"
        source_marker[str(source.id)] = marker
        citation_rows.append(
            {
                "marker": marker,
                "source_id": str(source.id),
                "title": source.title,
                "pmid": source.pmid,
                "doi": source.doi,
                "paper_id": str(source.paper_id) if source.paper_id else None,
            }
        )

    uncertainty = uncertainty_override or "Evidence certainty is limited by extraction quality, missing effect harmonization, and potential publication bias."
    limitations = limitations_override or "This consult is grounded only on retrieved sources and does not replace full critical appraisal."
    summary_text = actionable_summary or (
        f"{len(sources)} bibliographic sources were retrieved and prioritized. "
        "Use the claims below as a quick decision aid and confirm with full-text appraisal before changing care."
    )

    evidence_lines = [
        f"- [{idx}] {source.title or 'Untitled source'}"
        + (f" (PMID {source.pmid})" if source.pmid else "")
        + (f" — {_clip(source.excerpt, max_len=180)}" if source.excerpt else "")
        for idx, source in enumerate(sources, start=1)
    ]
    claim_lines = [
        f"- {_clip(claim.claim_text, max_len=220)} "
        f"{' '.join(source_marker.get(str(sid), '') for sid in (claim.source_ids_json or []))}".strip()
        + f" (confidence {round(float(claim.confidence or 0), 2)})"
        for claim in claims
    ]

    answer_lines = [
        f"### Clinical consult ({mode})",
        "",
        f"**Question:** {question}",
        "",
        f"**Actionable summary:** {summary_text}",
        "",
        "**Grounded claims:**",
    ]
    answer_lines.extend(claim_lines if claim_lines else ["- No grounded claims could be produced with the current evidence set."])
    answer_lines.extend(
        [
            "",
            "**Evidence used:**",
        ]
    )
    answer_lines.extend(evidence_lines if evidence_lines else ["- No evidence sources matched the question."])
    answer_lines.extend(
        [
            "",
            f"**Uncertainty:** {uncertainty}",
            f"**Limitations:** {limitations}",
        ]
    )
    answer_md = "\n".join(answer_lines)

    answer_json = {
        "question": question,
        "mode": mode,
        "actionable_summary": summary_text,
        "claims": [
            {
                "claim_text": item.claim_text,
                "confidence": item.confidence,
                "support_level": item.support_level,
                "source_count": item.evidence_count,
                "source_ids": item.source_ids_json or [],
            }
            for item in claims
        ],
        "citations": citation_rows,
        "uncertainty": uncertainty,
        "limitations": limitations,
    }
    return answer_md, answer_json, uncertainty, limitations


async def create_clinical_consult(
    db: AsyncSession,
    *,
    user_id: UUID,
    project_id: UUID | None,
    question: str,
    mode: str,
    pico_json: dict | None,
    use_project_library: bool,
    use_pubmed: bool,
) -> ClinicalConsult:
    if mode not in SUPPORTED_CONSULT_MODES:
        raise ValueError(f"Unsupported clinical consult mode: {mode}")
    if not question.strip():
        raise ValueError("question is required")

    source_limit, claim_limit = _answer_limits(mode)
    source_payloads: list[dict[str, Any]] = []

    if use_project_library and project_id:
        source_payloads.extend(
            await _collect_project_sources(
                db,
                question=question,
                project_id=project_id,
                limit=source_limit,
            )
        )

    if use_pubmed and len(source_payloads) < source_limit:
        pubmed_sources = await _collect_pubmed_sources(question=question, limit=source_limit - len(source_payloads))
        source_payloads.extend(pubmed_sources)

    consult = ClinicalConsult(
        project_id=project_id,
        user_id=user_id,
        question=question.strip(),
        mode=mode,
        status="completed",
        pico_json=pico_json or {},
        input_params={
            "use_project_library": bool(use_project_library),
            "use_pubmed": bool(use_pubmed),
        },
        used_project_library=bool(project_id and use_project_library),
        used_pubmed=bool(use_pubmed),
    )
    db.add(consult)
    await db.flush()

    source_models: list[ClinicalConsultSource] = []
    for idx, item in enumerate(source_payloads[:source_limit], start=1):
        source = ClinicalConsultSource(
            consult_id=consult.id,
            source_kind=item["source_kind"],
            paper_id=item.get("paper_id"),
            pmid=item.get("pmid"),
            doi=item.get("doi"),
            title=item.get("title"),
            authors=item.get("authors"),
            year=item.get("year"),
            url=item.get("url"),
            excerpt=item.get("excerpt"),
            locator_json=item.get("locator_json") or {},
            rank=idx,
            relevance=float(item.get("relevance") or 0),
            confidence=float(item.get("confidence") or 0),
            metadata_json={},
        )
        db.add(source)
        source_models.append(source)

    await db.flush()

    claim_models: list[ClinicalConsultClaim] = []
    llm_payload = await _llm_grounded_consult_payload(
        question=question.strip(),
        mode=mode,
        sources=source_models,
        claim_limit=claim_limit,
    )
    valid_source_ids = {str(source.id) for source in source_models}
    raw_llm_claims = llm_payload.get("claims") if isinstance(llm_payload, dict) else None
    if isinstance(raw_llm_claims, list):
        for raw_claim in raw_llm_claims[:claim_limit]:
            claim_text = _clip(str((raw_claim or {}).get("claim_text") or ""), max_len=260)
            source_ids = [sid for sid in ((raw_claim or {}).get("source_ids") or []) if str(sid) in valid_source_ids]
            if not claim_text or not source_ids:
                continue
            claim = ClinicalConsultClaim(
                consult_id=consult.id,
                claim_text=claim_text,
                support_level=str((raw_claim or {}).get("support_level") or "grounded_llm"),
                uncertainty=str((raw_claim or {}).get("uncertainty") or "moderate"),
                confidence=_safe_confidence((raw_claim or {}).get("confidence"), default=0.7),
                evidence_count=len(source_ids),
                source_ids_json=[str(sid) for sid in source_ids],
                metadata_json={"grounding_method": "llm_grounded_json"},
            )
            db.add(claim)
            claim_models.append(claim)

    if not claim_models:
        for source in source_models[:claim_limit]:
            if len((source.excerpt or "").strip()) < 24:
                continue
            claim_text = _build_claim(source.title or "Untitled source", source.excerpt or "")
            if not claim_text:
                continue
            claim = ClinicalConsultClaim(
                consult_id=consult.id,
                claim_text=claim_text,
                support_level="grounded_extract",
                uncertainty="moderate" if source.source_kind == "project_paper" else "moderate_to_high",
                confidence=max(0.35, min(0.95, float(source.confidence or 0.5))),
                evidence_count=1,
                source_ids_json=[str(source.id)],
                metadata_json={"grounding_method": "extractive_sentence"},
            )
            db.add(claim)
            claim_models.append(claim)

    await db.flush()

    answer_md, answer_json, uncertainty, limitations = _compose_answer(
        question=question.strip(),
        mode=mode,
        sources=source_models,
        claims=claim_models,
        actionable_summary=str(llm_payload.get("actionable_summary") or "").strip() if isinstance(llm_payload, dict) else None,
        uncertainty_override=str(llm_payload.get("uncertainty") or "").strip() if isinstance(llm_payload, dict) else None,
        limitations_override=str(llm_payload.get("limitations") or "").strip() if isinstance(llm_payload, dict) else None,
    )
    consult.answer_markdown = answer_md
    consult.answer_json = answer_json
    consult.uncertainty_text = uncertainty
    consult.limitations_text = limitations

    await db.commit()
    stmt = (
        select(ClinicalConsult)
        .where(ClinicalConsult.id == consult.id)
        .options(
            selectinload(ClinicalConsult.sources),
            selectinload(ClinicalConsult.claims),
        )
    )
    hydrated = await db.execute(stmt)
    return hydrated.scalars().first()


async def get_consult(db: AsyncSession, *, consult_id: UUID) -> ClinicalConsult | None:
    stmt = (
        select(ClinicalConsult)
        .where(ClinicalConsult.id == consult_id)
        .options(
            selectinload(ClinicalConsult.sources),
            selectinload(ClinicalConsult.claims),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_consults(
    db: AsyncSession,
    *,
    user_id: UUID,
    project_id: UUID | None,
) -> list[ClinicalConsult]:
    stmt = select(ClinicalConsult).where(ClinicalConsult.user_id == user_id)
    if project_id:
        stmt = stmt.where(ClinicalConsult.project_id == project_id)
    stmt = stmt.order_by(ClinicalConsult.created_at.desc()).options(
        selectinload(ClinicalConsult.sources),
        selectinload(ClinicalConsult.claims),
    )
    result = await db.execute(stmt)
    return result.scalars().all()


def serialize_consult(consult: ClinicalConsult) -> dict[str, Any]:
    return {
        "id": str(consult.id),
        "project_id": str(consult.project_id) if consult.project_id else None,
        "user_id": str(consult.user_id),
        "question": consult.question,
        "mode": consult.mode,
        "status": consult.status,
        "pico_json": consult.pico_json or {},
        "answer_markdown": consult.answer_markdown or "",
        "answer_json": consult.answer_json or {},
        "uncertainty_text": consult.uncertainty_text,
        "limitations_text": consult.limitations_text,
        "used_project_library": consult.used_project_library,
        "used_pubmed": consult.used_pubmed,
        "created_at": consult.created_at.isoformat() if consult.created_at else None,
        "updated_at": consult.updated_at.isoformat() if consult.updated_at else None,
        "sources": [
            {
                "id": str(item.id),
                "source_kind": item.source_kind,
                "paper_id": str(item.paper_id) if item.paper_id else None,
                "pmid": item.pmid,
                "doi": item.doi,
                "title": item.title,
                "authors": item.authors,
                "year": item.year,
                "url": item.url,
                "excerpt": item.excerpt,
                "rank": item.rank,
                "relevance": item.relevance,
                "confidence": item.confidence,
            }
            for item in consult.sources
        ],
        "claims": [
            {
                "id": str(item.id),
                "claim_text": item.claim_text,
                "support_level": item.support_level,
                "uncertainty": item.uncertainty,
                "confidence": item.confidence,
                "evidence_count": item.evidence_count,
                "source_ids": item.source_ids_json or [],
            }
            for item in consult.claims
        ],
    }

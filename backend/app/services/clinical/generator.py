from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models.book_index import BookIndex
from app.models.note import Note
from app.models.paper import Paper
from app.models.search import SearchResult
from app.services.books.indexer import extract_pages_text
from app.services.clinical.prompts import (
    auditor_system_prompt,
    auditor_user_message,
    clinical_system_prompt,
    clinical_user_message,
)
from app.services.clinical.sections import sections_for
from app.services.llm.openclaw import OpenClawProvider
from app.services.pubmed import pubmed_client


def _keywords(topic: str) -> list[str]:
    toks = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ\-]{2,}", topic.lower())
    # de-dupe keep order
    out: list[str] = []
    for t in toks:
        if t not in out:
            out.append(t)
    return out[:20]


def _score(text: str, keys: list[str]) -> int:
    t = (text or "").lower()
    return sum(t.count(k) for k in keys)


async def _collect_project_papers(db: AsyncSession, project_id, topic: str, *, max_papers: int = 10) -> list[dict[str, Any]]:
    keys = _keywords(topic)

    stmt = select(Paper, SearchResult).join(SearchResult, SearchResult.id == Paper.search_result_id, isouter=True).where(Paper.project_id == project_id)
    q = await db.execute(stmt)
    rows = q.all()

    scored: list[tuple[int, Paper, SearchResult | None]] = []
    for p, sr in rows:
        s = 0
        s += 5 * _score(p.title or "", keys)
        if sr and sr.abstract:
            s += 2 * _score(sr.abstract, keys)
        if p.full_text_extracted:
            s += 1 * _score(p.full_text_extracted[:5000], keys)
        scored.append((s, p, sr))

    scored.sort(key=lambda x: (x[0], x[1].downloaded_at or x[1].created_at), reverse=True)

    top_papers = scored[:max_papers]
    paper_ids = [p.id for s, p, sr in top_papers]

    # fetch all summary notes for the top papers in one go
    notes_by_paper = {}
    if paper_ids:
        qn = await db.execute(
            select(Note)
            .where(Note.paper_id.in_(paper_ids), Note.note_type == "summary")
            .order_by(Note.paper_id, Note.created_at.desc())
        )
        notes = qn.scalars().all()
        for note in notes:
            if note.paper_id not in notes_by_paper:
                notes_by_paper[note.paper_id] = note

    out: list[dict[str, Any]] = []
    for s, p, sr in top_papers:
        note = notes_by_paper.get(p.id)

        ft = (p.full_text_extracted or "").strip()
        out.append(
            {
                "paper_id": str(p.id),
                "title": p.title,
                "doi": p.doi,
                "pmid": p.pmid,
                "pmcid": p.pmcid,
                "abstract": (sr.abstract if sr else None),
                "summary_note": (note.content[:4000] if note else None),
                "has_full_text": bool(ft),
                "full_text_excerpt": (ft[:12000] if ft else None),
            }
        )

    return out


async def _collect_book_fragments(db: AsyncSession, user_id, topic: str, *, max_chapters: int = 5, max_chars: int = 12000) -> list[dict[str, Any]]:
    keys = _keywords(topic)
    q = await db.execute(select(BookIndex).where(BookIndex.user_id == user_id))
    books = q.scalars().all()

    scored: list[tuple[int, BookIndex, dict]] = []
    for b in books:
        for ch in (b.chapters or []):
            kws = [str(k).lower() for k in (ch.get("keywords") or [])]
            overlap = len(set(keys).intersection(set(kws)))
            # basic weight with title match
            overlap += _score(str(ch.get("title") or ""), keys)
            if overlap > 0:
                scored.append((overlap, b, ch))

    scored.sort(key=lambda x: x[0], reverse=True)

    out: list[dict[str, Any]] = []
    for score, b, ch in scored[:max_chapters]:
        try:
            from app.core.storage import storage_manager

            abs_path = (storage_manager.base_dir / b.file_path).resolve()
            abs_path.relative_to(storage_manager.base_dir)
            frag = extract_pages_text(
                abs_path,
                int(ch.get("page_start") or 1),
                int(ch.get("page_end") or 1),
                max_chars=int(max_chars),
            )
        except Exception as e:
            logger.warning(f"Book fragment extraction failed book={b.id}: {e}")
            frag = ""

        out.append(
            {
                "book_id": str(b.id),
                "filename": b.filename,
                "title": b.title,
                "chapter_title": ch.get("title"),
                "page_start": ch.get("page_start"),
                "page_end": ch.get("page_end"),
                "score": score,
                "text": frag,
            }
        )

    return out


def _generate_pubmed_queries(topic: str, region: str | None) -> list[str]:
    """Generate 5–10 PubMed queries from a topic (best-effort).

    We avoid inventing MeSH terms; instead we generate safe variants and subqueries.
    """

    base = (topic or "").strip()
    if region:
        base = f"{base} {region}".strip()

    # Common clinical intents
    intents = [
        "diagnosis",
        "treatment",
        "management",
        "practice guideline",
        "systematic review",
        "meta-analysis",
        "randomized controlled trial",
        "rehabilitation",
    ]

    queries: list[str] = []
    queries.append(base)
    for it in intents:
        queries.append(f"{base} {it}")

    # Keep unique + cap
    out: list[str] = []
    for q in queries:
        q = " ".join(q.split())
        if q and q not in out:
            out.append(q)
    return out[:10]


def _study_type_rank(pub_types: list[str] | None, title: str | None) -> int:
    pts = [str(x).lower() for x in (pub_types or [])]
    t = (title or "").lower()

    # Higher is better
    if any("practice guideline" in p or p == "guideline" for p in pts) or "guideline" in t:
        return 6
    if any("systematic review" in p for p in pts) or "systematic review" in t:
        return 5
    if any("meta-analysis" in p or "meta analysis" in p for p in pts) or "meta-analysis" in t:
        return 5
    if any("randomized controlled trial" in p for p in pts) or "randomized" in t or "randomised" in t:
        return 4
    if any(p == "review" or "review" in p for p in pts) or "review" in t:
        return 3
    # cohort/case-control are not reliably labeled in PublicationType; keep default
    return 2


def _score_pubmed_item(*, topic: str, it: dict[str, Any]) -> int:
    from datetime import datetime, timezone

    now_year = datetime.now(timezone.utc).year
    keys = _keywords(topic)

    title = it.get("title")
    abstract = it.get("abstract")
    pub_year = it.get("pub_year")
    pub_types = it.get("publication_types") or []

    score = 0

    # Relevance
    score += 6 * _score(str(title or ""), keys)
    score += 2 * _score(str(abstract or ""), keys)

    # Penalize missing abstract (common in low-value hits)
    if not (abstract or "").strip():
        score -= 6

    # Study type
    tr = _study_type_rank(pub_types, title)
    score += 6 * tr

    # Recency boost (strong last 5y, then 10y)
    try:
        if pub_year:
            years_ago = max(0, now_year - int(pub_year))
            if years_ago <= 5:
                score += 10
            elif years_ago <= 10:
                score += 5
    except Exception:
        pass

    # OA bonus small
    if it.get("is_open_access"):
        score += 2

    return int(score)


async def _collect_pubmed_multi(
    topic: str,
    region: str | None,
    *,
    per_query_max: int = 25,
    total_cap: int = 80,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Multi-query PubMed search with dedup + scoring.

    Returns: (top25, core10)
    """

    queries = _generate_pubmed_queries(topic, region)

    all_items: list[dict[str, Any]] = []
    for q in queries:
        try:
            data = await pubmed_client.search_and_fetch(query=q, max_results=per_query_max)
            all_items.extend(data.get("results") or [])
        except Exception as e:
            logger.info(f"PubMed multi-query failed query={q}: {e}")

    # Dedup by PMID (and fallback DOI)
    by_key: dict[str, dict[str, Any]] = {}
    for it in all_items[:total_cap * 3]:
        pmid = str(it.get("pmid") or "").strip()
        doi = str(it.get("doi") or "").strip().lower()
        key = pmid or (f"doi:{doi}" if doi else "")
        if not key:
            continue
        if key not in by_key:
            by_key[key] = dict(it)

    deduped = list(by_key.values())

    scored: list[dict[str, Any]] = []
    for it in deduped:
        it2 = dict(it)
        it2["score"] = _score_pubmed_item(topic=topic, it=it2)
        it2["study_type_rank"] = _study_type_rank(it2.get("publication_types") or [], it2.get("title"))
        scored.append(it2)

    scored.sort(key=lambda x: (x.get("score") or 0, x.get("pub_year") or 0), reverse=True)

    top25 = scored[:25]
    core10 = scored[:10]
    return top25, core10


async def _collect_pubmed(topic: str, region: str | None, *, max_results: int = 25) -> list[dict[str, Any]]:
    """Back-compat helper: return ranked top results (top25)."""

    top25, _core10 = await _collect_pubmed_multi(topic, region, per_query_max=max_results, total_cap=120)
    return top25


def _excerpt(text: str, keys: list[str], *, max_chars: int = 4000) -> str:
    t = (text or "").strip()
    if not t:
        return ""

    tlow = t.lower()
    pos = None
    for k in keys:
        p = tlow.find(k)
        if p != -1:
            pos = p if pos is None else min(pos, p)

    if pos is None:
        return t[:max_chars]

    start = max(0, pos - 900)
    end = min(len(t), pos + 2600)
    out = t[start:end]
    if start > 0:
        out = "…" + out
    if end < len(t):
        out = out + "…"
    return out[:max_chars]


async def _collect_oa_full_text(
    *,
    topic: str,
    pubmed_results: list[dict[str, Any]],
    max_full_texts: int = 3,
) -> list[dict[str, Any]]:
    """Try to download and extract OA full text for top PubMed results."""

    keys = _keywords(topic)
    out: list[dict[str, Any]] = []

    # only OA candidates with at least one identifier
    # Try OA for the most relevant results; resolvers will reject non-OA.
    cands = [r for r in (pubmed_results or []) if (r.get("doi") or r.get("pmid"))]
    cands.sort(key=lambda x: (x.get("score") or 0), reverse=True)

    from app.services.paper_service import PaperDownloadService

    downloader = PaperDownloadService()

    import httpx
    import tempfile
    from pathlib import Path

    from app.services.pdf_processor import extract_text

    async with httpx.AsyncClient() as client:
        for r in cands[: max_full_texts * 2]:
            if len(out) >= max_full_texts:
                break
            pmid = r.get("pmid")
            doi = r.get("doi")
            try:
                dl = await downloader.download_open_access_pdf(doi=doi, pmid=pmid, client=client)
                with tempfile.TemporaryDirectory() as td:
                    p = Path(td) / "oa.pdf"
                    p.write_bytes(dl.pdf_bytes)
                    text = extract_text(p)

                out.append(
                    {
                        "pmid": pmid,
                        "doi": doi,
                        "resolved_url": dl.resolved_url,
                        "source": dl.source,
                        "excerpt": _excerpt(text, keys, max_chars=4500),
                        "chars": len(text or ""),
                    }
                )
            except Exception as e:
                # ignore individual failures
                logger.info(f"OA full text failed pmid={pmid} doi={doi}: {e}")
                continue

    return out


def _safe_json_loads(text: str) -> Any:
    t = (text or "").strip()
    try:
        return json.loads(t)
    except Exception:
        # extract first { .. }
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(t[start : end + 1])
        raise


async def generate_clinical_sheet(
    *,
    db: AsyncSession,
    sheet,
    progress_cb: Callable[[int], Any] | None = None,
) -> dict[str, Any]:
    """Generate content for a ClinicalSheet.

    Returns dict with: content_markdown, references_json, sources_used, llm_model, llm_usage, warnings
    """

    import inspect

    async def prog(p: int) -> None:
        if not progress_cb:
            return
        try:
            r = progress_cb(int(p))
            if inspect.isawaitable(r):
                await r
        except Exception:
            # best-effort
            return

    params = sheet.input_params or {}
    topic = sheet.topic
    context = params.get("context")
    objective = params.get("objective") or "clinical_decision"
    level = params.get("level") or "specialist"
    focus = params.get("focus") or "complete"
    region = params.get("region")
    max_length = params.get("max_length") or "standard"

    use_project_papers = bool(params.get("use_project_papers", True))
    search_online = bool(params.get("search_online", True))
    use_books = bool(params.get("use_books", True))

    await prog(10)

    # 1) Project papers (primary)
    paper_bundle: list[dict[str, Any]] = []
    if sheet.project_id and use_project_papers:
        paper_bundle = await _collect_project_papers(db, sheet.project_id, topic, max_papers=12)

    await prog(18)

    # 2) PubMed (multi-query) (metadata + abstract)
    pubmed_top25: list[dict[str, Any]] = []
    pubmed_core10: list[dict[str, Any]] = []
    if search_online:
        pubmed_top25, pubmed_core10 = await _collect_pubmed_multi(topic, region, per_query_max=25, total_cap=120)

    await prog(24)

    # 3) OA full text when available (prioritize core10, then top25)
    oa_full_text: list[dict[str, Any]] = []
    if search_online and (pubmed_core10 or pubmed_top25):
        oa_full_text = await _collect_oa_full_text(
            topic=topic,
            pubmed_results=(pubmed_core10 + [x for x in pubmed_top25 if x not in pubmed_core10]),
            max_full_texts=6,
        )

    await prog(30)

    # 4) Books (only if already indexed in system) — secondary only
    book_fragments: list[dict[str, Any]] = []
    if use_books:
        articles_available = bool(paper_bundle) or bool(pubmed_core10) or bool(pubmed_top25) or bool(oa_full_text)
        book_fragments = await _collect_book_fragments(db, sheet.user_id, topic, max_chapters=(2 if articles_available else 5), max_chars=5000)

    sections = sections_for(objective=objective, focus=focus)

    evidence_bundle = {
        "project_papers": paper_bundle,
        "pubmed_top25": pubmed_top25,
        "pubmed_core10": pubmed_core10,
        "oa_full_text": oa_full_text,
        "local_books": book_fragments,
        "requested_sections": sections,
    }

    await prog(35)

    # PRO mode (structured JSON + 4-pass ensemble)
    use_pro = bool(params.get("pro_output", True))

    warnings: list[str] = []

    # Always compute sources_used deterministically (for transparency)
    sources_used = {
        "papers": [{"paper_id": p.get("paper_id"), "doi": p.get("doi"), "pmid": p.get("pmid"), "pmcid": p.get("pmcid")} for p in paper_bundle],
        "pubmed_core10": [{"pmid": o.get("pmid"), "doi": o.get("doi"), "pub_year": o.get("pub_year"), "publication_types": o.get("publication_types"), "score": o.get("score")} for o in pubmed_core10],
        "pubmed_top25": [{"pmid": o.get("pmid"), "doi": o.get("doi"), "pub_year": o.get("pub_year"), "publication_types": o.get("publication_types"), "score": o.get("score")} for o in pubmed_top25],
        "oa_full_text": [{"pmid": o.get("pmid"), "doi": o.get("doi"), "resolved_url": o.get("resolved_url"), "source": o.get("source"), "chars": o.get("chars")} for o in oa_full_text],
        "books": [{"book_id": b.get("book_id"), "chapter_title": b.get("chapter_title"), "page_start": b.get("page_start"), "page_end": b.get("page_end")} for b in book_fragments],
        "queries": {"generated": _generate_pubmed_queries(topic, region)},
    }

    if use_pro:
        from app.services.clinical.pro_pipeline import generate_clinical_pro_output
        from app.services.clinical.pro_gates import (
            gate_article_dominance,
            gate_citations_per_section,
            gate_claim_traceability,
            gate_min_assets,
            gate_min_evidence_map,
            gate_min_sections,
        )
        from app.services.clinical.pro_render import render_pro_to_markdown

        await prog(40)

        pro_out, pro_usage, pro_warnings = await generate_clinical_pro_output(
            topic=topic,
            context=context,
            region=region,
            evidence_bundle=evidence_bundle,
            objective=str(objective),
            focus=str(focus),
            level=str(level),
            max_length=str(max_length),
            progress_cb=lambda p, label: prog(p),
        )
        warnings.extend(pro_warnings)

        await prog(75)

        pro_out, w1 = gate_min_sections(pro_out)
        warnings.extend(w1)
        pro_out, w2 = gate_min_assets(pro_out)
        warnings.extend(w2)
        pro_out, w2b = gate_min_evidence_map(pro_out)
        warnings.extend(w2b)
        pro_out, w3 = gate_citations_per_section(pro_out)
        warnings.extend(w3)
        pro_out, w3b = gate_claim_traceability(pro_out, core_papers=pubmed_core10)
        warnings.extend(w3b)
        pro_out, w4 = gate_article_dominance(pro_out)
        warnings.extend(w4)

        md = render_pro_to_markdown(pro_out)

        await prog(90)

        return {
            "content_markdown": md,
            "content_json": pro_out.model_dump(),
            "format_version": "clinical_pro_v1",
            "references_json": [],
            "sources_used": sources_used,
            "llm_model": "ensemble",
            "llm_usage": pro_usage,
            "warnings": warnings,
        }

    # Fallback legacy mode
    oc = OpenClawProvider()

    sys1 = clinical_system_prompt(level=str(level), focus=str(focus), objective=str(objective), max_length=str(max_length))
    usr1 = clinical_user_message(topic=topic, context=context, region=region, evidence_bundle=evidence_bundle)

    r1 = await oc.chat(model="default", system=sys1, user=usr1, temperature=0.2, max_tokens=4096, timeout=360, retry=2)
    d1 = _safe_json_loads(r1.get("content") or "")

    content_md = str(d1.get("content_markdown") or "").strip()
    references_json = d1.get("references_json")
    vancouver = d1.get("vancouver")

    if not content_md:
        raise RuntimeError("LLM returned empty content_markdown")

    await prog(70)

    # Audit pass
    sys2 = auditor_system_prompt()
    usr2 = auditor_user_message(draft_content_markdown=content_md, references_json=references_json if isinstance(references_json, list) else [])
    r2 = await oc.chat(model="default", system=sys2, user=usr2, temperature=0.0, max_tokens=2048, timeout=240, retry=2)
    audit = _safe_json_loads(r2.get("content") or "")

    fixed_md = content_md
    fixed_refs = references_json

    if isinstance(audit, dict) and audit.get("ok") is False:
        fixed_md = str(audit.get("fixed_content_markdown") or content_md)
        fixed_refs = audit.get("fixed_references_json") or references_json
        warnings.append("Clinical sheet was auto-corrected by auditor pass.")

    await prog(86)

    from app.services.clinical.assets_gate import ensure_assets_present
    from app.services.clinical.citations_gate import ensure_fuentes_per_section

    fixed_md, assets_warnings = ensure_assets_present(fixed_md, topic=str(topic))
    warnings.extend(assets_warnings)

    fixed_md, gate_warnings = ensure_fuentes_per_section(fixed_md)
    warnings.extend(gate_warnings)

    usage = {"pass1": r1.get("usage"), "pass2": r2.get("usage")}

    if "## Referencias" not in fixed_md and isinstance(vancouver, list):
        fixed_md = fixed_md.rstrip() + "\n\n## Referencias\n\n" + "\n".join([str(x) for x in vancouver])

    return {
        "content_markdown": fixed_md,
        "content_json": None,
        "format_version": None,
        "references_json": fixed_refs,
        "sources_used": sources_used,
        "llm_model": "default",
        "llm_usage": usage,
        "warnings": warnings,
    }

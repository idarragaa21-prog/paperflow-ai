"""Deep Research Report generator.

Orchestrates: PubMed search OR project library → paper analysis → structured report.
Supports two source modes:
  - "pubmed"  (default): searches PubMed fresh for max_papers results
  - "project": uses papers already downloaded in a given project (full_text when
               available, abstract_text as fallback)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logger import logger


# ── Report section templates ──────────────────────────────────────────────────

REPORT_SECTIONS = [
    {
        "key": "overview",
        "title": "Research Overview",
        "prompt": "Based on the following papers about '{query}', write a comprehensive research overview paragraph (200-300 words) that summarizes the current state of knowledge, key themes, and scope of the literature. Include the total number of papers analyzed.",
    },
    {
        "key": "key_findings",
        "title": "Key Findings",
        "prompt": "Based on the following papers about '{query}', identify and describe the 5-8 most important findings across the literature. For each finding, cite the specific paper(s) that support it. Format as structured paragraphs, not bullet points.",
    },
    {
        "key": "methodology",
        "title": "Methodology Trends",
        "prompt": "Based on the following papers about '{query}', analyze the methodological approaches used across the literature. Identify: most common study designs, sample sizes, statistical methods, and any methodological limitations or gaps.",
    },
    {
        "key": "consensus",
        "title": "Consensus & Controversies",
        "prompt": "Based on the following papers about '{query}', identify areas of strong consensus among researchers and any active controversies or conflicting findings. Explain the nature of each disagreement and which evidence supports each side.",
    },
    {
        "key": "gaps",
        "title": "Research Gaps & Future Directions",
        "prompt": "Based on the following papers about '{query}', identify 3-5 clear gaps in the current literature and suggest specific future research directions that would address these gaps.",
    },
    {
        "key": "conclusion",
        "title": "Conclusion",
        "prompt": "Based on the following papers about '{query}', write a concise conclusion (150-200 words) that synthesizes the overall state of the evidence, clinical/practical implications, and the most pressing next steps for the field.",
    },
]


# ── Paper sources ─────────────────────────────────────────────────────────────

async def search_papers_pubmed(query: str, max_results: int = 20) -> list[dict]:
    """Search PubMed and return structured paper metadata."""
    from app.services.pubmed import PubMedClient
    client = PubMedClient()
    try:
        payload = await client.search_and_fetch(query=query, max_results=max_results)
        results = payload.get("results") or []
        return [
            {
                "pmid": r.get("pmid", ""),
                "doi": r.get("doi", ""),
                "title": r.get("title", ""),
                "authors": ", ".join(r.get("authors") or []),
                "journal": r.get("journal", ""),
                "year": str(r.get("pub_year") or ""),
                "abstract": r.get("abstract", ""),
                "source": "pubmed",
                "oa_url": r.get("oa_url"),
                "has_full_text": bool(r.get("is_open_access")),
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


async def load_papers_from_project(project_id: str, db: AsyncSession) -> list[dict]:
    """Load papers already downloaded in a project, preferring full text."""
    from uuid import UUID
    from app.models.paper import Paper
    from app.models.search import SearchResult

    try:
        proj_uuid = UUID(project_id)
    except ValueError:
        logger.error(f"Invalid project_id: {project_id}")
        return []

    stmt = (
        select(Paper, SearchResult)
        .join(SearchResult, SearchResult.id == Paper.search_result_id, isouter=True)
        .where(Paper.project_id == proj_uuid)
        .order_by(Paper.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    papers = []
    for p, sr in rows:
        # Use full extracted text when available; fall back to abstract
        body = ""
        if p.full_text_extracted:
            body = p.full_text_extracted[:8000]
        elif p.abstract_text:
            body = p.abstract_text
        elif sr and sr.abstract:
            body = sr.abstract

        authors = p.authors or ""
        papers.append({
            "pmid": p.pmid or "",
            "doi": p.doi or "",
            "title": p.title or "Untitled",
            "authors": authors,
            "journal": p.journal or "",
            "year": str(p.publication_year or ""),
            "abstract": body,
            "source": "project_library",
            "has_full_text": bool(p.full_text_extracted),
        })

    logger.info(f"[DeepResearch] Loaded {len(papers)} papers from project {project_id}")
    return papers


# ── Context builder ───────────────────────────────────────────────────────────

def build_papers_context(papers: list[dict], max_papers: int = 12) -> str:
    """Build LLM-ready context from paper abstracts / full text."""
    parts = []
    for i, p in enumerate(papers[:max_papers], 1):
        authors_short = (p.get("authors") or "Unknown")
        if len(authors_short) > 80:
            authors_short = authors_short[:80] + "…"

        body = p.get("abstract") or "No abstract available"
        has_ft = p.get("has_full_text")
        label = "[FULL TEXT EXCERPT]" if has_ft else "[ABSTRACT]"

        parts.append(
            f"[{i}] {p['title']}\n"
            f"    Authors: {authors_short}\n"
            f"    Journal: {p.get('journal', 'N/A')} ({p.get('year', 'N/A')})\n"
            f"    PMID: {p.get('pmid') or 'N/A'}  DOI: {p.get('doi') or 'N/A'}\n"
            f"    Source: {p.get('source', 'pubmed')}  {label}\n"
            f"    {body}\n"
        )
    return "\n".join(parts)


# ── LLM section generator ─────────────────────────────────────────────────────

async def _generate_section(section_prompt: str, papers_context: str, query: str) -> str:
    """Generate one report section via the configured LLM provider."""
    from app.services.llm.factory import llm_provider

    system = (
        "You are an expert research analyst generating a deep research report. "
        "Write in clear, professional academic English. "
        "Always cite specific papers by their number [1], [2], etc."
    )
    user = (
        f"{section_prompt.replace('{query}', query)}\n\n"
        f"PAPERS:\n{papers_context}\n\n"
        "Write in a professional academic tone. Cite papers by number [1], [2], etc. "
        "Be specific and evidence-based. Do NOT invent data not present in the papers."
    )

    try:
        provider = llm_provider()
        # All providers have summarize_paper but not a generic chat.
        # Use the OpenClaw provider's chat() if available, else fall back to a
        # summary-like call by reusing the paper summarization system.
        if hasattr(provider, "chat"):
            try:
                r = await provider.chat(  # type: ignore[attr-defined]
                    model="default",
                    system=system,
                    user=user,
                    temperature=0.3,
                    max_tokens=1500,
                )
                return (r.get("content") or "").strip()
            except Exception as primary_exc:
                logger.warning(f"Deep Research primary chat provider failed, falling back to Ollama: {primary_exc}")
                from app.services.llm.provider_adapters import OllamaAdapter, CompletionRequest

                fallback = OllamaAdapter(settings.PAPERFLOW_CHAT_MODEL, base_url=settings.OLLAMA_BASE_URL)
                req = CompletionRequest(
                    prompt=user,
                    system=system,
                    temperature=0.3,
                    max_tokens=1500,
                    json_mode=False,
                )
                response = await fallback.complete(req)
                return response.text.strip()
        else:
            # Fallback: describe the inability gracefully
            return f"*LLM provider does not support direct chat. Configure OpenClaw or Claude provider.*"
    except Exception as e:
        logger.error(f"LLM generation failed for section: {e}")
        return f"*Section could not be generated: {e}*"


# ── Main entry point ──────────────────────────────────────────────────────────


@dataclass
class DeepResearchParams:
    query: str
    max_papers: int = 15
    source_mode: str = "pubmed"
    project_id: str | None = None
    db: AsyncSession | None = None
    progress_callback: Any | None = None

async def generate_deep_research_report(params: DeepResearchParams) -> dict:
    """Full pipeline: source papers → build context → generate report sections.

    Args:
        params: DeepResearchParams instance containing all configuration and dependencies.
    """
    query = params.query
    max_papers = params.max_papers
    source_mode = params.source_mode
    project_id = params.project_id
    db = params.db
    progress_callback = params.progress_callback

    report_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    def prog(step: str, pct: int):
        if progress_callback:
            try:
                progress_callback(step=step, percent=pct)
            except Exception:
                pass

    # ── Step 1: Collect papers ────────────────────────────────────────────────
    if source_mode == "project":
        if not project_id or not db:
            return {
                "id": report_id, "query": query, "status": "error",
                "error": "project_id and db session are required for source_mode='project'.",
                "sections": [], "papers": [],
                "metadata": {"started_at": started_at.isoformat()},
            }
        prog("Loading papers from project library…", 10)
        papers = await load_papers_from_project(project_id, db)
        source_label = "project_library"
    else:
        prog("Searching PubMed…", 10)
        logger.info(f"[DeepResearch] PubMed search: {query}")
        papers = await search_papers_pubmed(query, max_results=max_papers)
        source_label = "pubmed"

    if not papers:
        msg = (
            "No papers found in this project. Add papers to the library first."
            if source_mode == "project"
            else "No papers found for this query. Try different keywords."
        )
        return {
            "id": report_id, "query": query, "status": "error", "error": msg,
            "sections": [], "papers": [],
            "metadata": {"started_at": started_at.isoformat(), "source": source_label},
        }

    prog(f"Found {len(papers)} papers. Analyzing…", 25)
    papers_context = build_papers_context(papers, max_papers=12)

    # ── Step 2: Generate sections ─────────────────────────────────────────────
    sections: list[dict] = []
    total = len(REPORT_SECTIONS)
    for i, sec in enumerate(REPORT_SECTIONS):
        pct = 30 + int((i / total) * 60)
        prog(f"Generating: {sec['title']}…", pct)
        logger.info(f"[DeepResearch] Section: {sec['key']}")
        content = await _generate_section(sec["prompt"], papers_context, query)
        sections.append({"key": sec["key"], "title": sec["title"], "content": content})

    prog("Finalizing report…", 95)
    completed_at = datetime.now(timezone.utc)

    return {
        "id": report_id,
        "query": query,
        "status": "completed",
        "sections": sections,
        "papers": papers,
        "papers_analyzed": len(papers),
        "source_mode": source_label,
        "metadata": {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "source": source_label,
            "project_id": project_id,
        },
    }

"""Deep Research Report generator.

Orchestrates: PubMed search → paper analysis → structured report generation.
Designed to run as a background job via RQ.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.services.pubmed import PubMedClient


# Report section templates
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


async def search_papers(query: str, max_results: int = 20) -> list[dict]:
    """Search PubMed and return structured paper metadata."""
    client = PubMedClient()
    try:
        results = await client.search(query=query, max_results=max_results)
        papers = []
        for r in results:
            papers.append({
                "pmid": r.get("pmid", ""),
                "title": r.get("title", ""),
                "authors": r.get("authors", ""),
                "journal": r.get("journal", ""),
                "year": r.get("year", ""),
                "abstract": r.get("abstract", ""),
            })
        return papers
    except Exception as e:
        logger.error(f"PubMed search failed: {e}")
        return []


def build_papers_context(papers: list[dict], max_papers: int = 10) -> str:
    """Build a text context from paper abstracts for LLM consumption."""
    context_parts = []
    for i, p in enumerate(papers[:max_papers], 1):
        authors_short = p.get("authors", "Unknown")
        if len(authors_short) > 80:
            authors_short = authors_short[:80] + "..."
        context_parts.append(
            f"[{i}] {p['title']}\n"
            f"    Authors: {authors_short}\n"
            f"    Journal: {p.get('journal', 'N/A')} ({p.get('year', 'N/A')})\n"
            f"    PMID: {p.get('pmid', 'N/A')}\n"
            f"    Abstract: {p.get('abstract', 'No abstract available')}\n"
        )
    return "\n".join(context_parts)


async def generate_section_with_llm(
    section_prompt: str,
    papers_context: str,
    query: str,
) -> str:
    """Generate a single report section using the configured LLM."""
    from app.services.llm.factory import get_llm_client

    client = get_llm_client()

    full_prompt = (
        f"{section_prompt.replace('{query}', query)}\n\n"
        f"PAPERS:\n{papers_context}\n\n"
        f"Write in a professional academic tone. Cite papers by their number [1], [2], etc. "
        f"Be specific and evidence-based."
    )

    try:
        response = await client.complete(
            prompt=full_prompt,
            system="You are an expert research analyst generating a deep research report. "
            "Write in clear, professional academic English. Always cite specific papers by their number.",
            max_tokens=1500,
        )
        return response.strip()
    except Exception as e:
        logger.error(f"LLM generation failed for section: {e}")
        return f"*Section could not be generated: {e}*"


async def generate_deep_research_report(
    query: str,
    max_papers: int = 15,
    progress_callback: Any | None = None,
) -> dict:
    """
    Full pipeline: search → analyze → generate report.

    Returns a structured report dict with sections, papers, and metadata.
    """
    report_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    def update_progress(step: str, pct: int):
        if progress_callback:
            try:
                progress_callback(step=step, percent=pct)
            except Exception:
                pass

    # Step 1: Search
    update_progress("Searching PubMed...", 10)
    logger.info(f"[DeepResearch] Searching: {query}")
    papers = await search_papers(query, max_results=max_papers)

    if not papers:
        return {
            "id": report_id,
            "query": query,
            "status": "error",
            "error": "No papers found for this query. Try different keywords.",
            "sections": [],
            "papers": [],
            "metadata": {"started_at": started_at.isoformat(), "completed_at": datetime.now(timezone.utc).isoformat()},
        }

    update_progress(f"Found {len(papers)} papers. Analyzing...", 25)
    papers_context = build_papers_context(papers, max_papers=10)

    # Step 2: Generate each section
    sections = []
    total_sections = len(REPORT_SECTIONS)
    for i, section_def in enumerate(REPORT_SECTIONS):
        step_pct = 30 + int((i / total_sections) * 60)
        update_progress(f"Generating: {section_def['title']}...", step_pct)
        logger.info(f"[DeepResearch] Generating section: {section_def['key']}")

        content = await generate_section_with_llm(
            section_prompt=section_def["prompt"],
            papers_context=papers_context,
            query=query,
        )

        sections.append({
            "key": section_def["key"],
            "title": section_def["title"],
            "content": content,
        })

    update_progress("Finalizing report...", 95)

    completed_at = datetime.now(timezone.utc)

    report = {
        "id": report_id,
        "query": query,
        "status": "completed",
        "sections": sections,
        "papers": papers,
        "papers_analyzed": len(papers),
        "metadata": {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "model": "configured LLM",
        },
    }

    update_progress("Done!", 100)
    logger.info(f"[DeepResearch] Report {report_id} completed in {report['metadata']['duration_seconds']:.1f}s")

    return report

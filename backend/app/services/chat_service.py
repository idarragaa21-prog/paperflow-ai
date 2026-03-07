from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.chat import AnswerCitation, ChatMessage, ChatSession, PaperHighlight, RetrievedChunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.services.model_router import resolve_model
from app.services.vector_index import vector_index


def _detect_claim_type(question: str, *, grounded: bool) -> str:
    lowered = question.lower()
    if any(token in lowered for token in ["why", "por qué", "implica", "interpret"]):
        return "inferencia" if grounded else "dato"
    if any(token in lowered for token in ["summary", "resumen", "overview", "sintetiza"]):
        return "resumen"
    return "dato"


def _extractive_snippet(text: str, query: str) -> str:
    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", text) if segment.strip()]
    query_terms = {term.lower() for term in query.split() if len(term) > 2}
    ranked: list[tuple[int, str]] = []
    for sentence in sentences:
        lowered = sentence.lower()
        score = sum(lowered.count(term) for term in query_terms)
        ranked.append((score, sentence))
    ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    return ranked[0][1] if ranked else text[:280].strip()


def _compose_grounded_answer(question: str, retrieved: list[dict], *, max_citations: int) -> tuple[str, float, str | None]:
    strong_hits = [item for item in retrieved if float(item.get("final_score") or item.get("score") or 0.0) >= settings.CHAT_MIN_GROUNDED_SCORE]
    if len(strong_hits) < settings.CHAT_MIN_RETRIEVED_CHUNKS:
        return (
            "No hay soporte documental suficiente para responder en modo evidence-based. Amplia la selección o procesa mejor el PDF.",
            0.0,
            "insufficient_grounding",
        )

    snippets: list[str] = []
    for item in strong_hits[:max_citations]:
        snippet = _extractive_snippet(str(item.get("quoted_text") or ""), question)
        if snippet and snippet not in snippets:
            snippets.append(snippet)
    answer = " ".join(snippets[:max_citations]).strip()
    confidence = min(0.98, 0.45 + (0.12 * min(len(strong_hits), max_citations)))
    return answer, confidence, None


async def _get_or_create_session(
    db: AsyncSession,
    *,
    project: Project,
    paper: Paper | None,
    user: User,
    session_id: UUID | None,
    task_type: str,
) -> ChatSession:
    if session_id is not None:
        session = await db.get(ChatSession, session_id)
        if not session or session.project_id != project.id or session.user_id != user.id:
            raise ValueError("Chat session not found")
        return session

    session = ChatSession(
        project_id=project.id,
        paper_id=paper.id if paper else None,
        user_id=user.id,
        title=(paper.title if paper else project.title)[:255],
        task_type=task_type,
        runtime_mode=project.runtime_mode,
        grounded=True,
        metadata_json={"scope": "paper" if paper else "project", "mode": settings.CHAT_DEFAULT_MODE},
    )
    db.add(session)
    await db.flush()
    return session


async def ask(
    db: AsyncSession,
    *,
    project: Project,
    paper: Paper | None,
    user: User,
    question: str,
    session_id: UUID | None,
    task_type: str,
    max_citations: int,
) -> dict:
    session = await _get_or_create_session(
        db,
        project=project,
        paper=paper,
        user=user,
        session_id=session_id,
        task_type=task_type,
    )
    route = resolve_model(task_type, project.runtime_mode)

    user_message = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role="user",
        content=question,
        claim_type="dato",
        confidence=1.0,
        grounded=False,
        metadata_json={"route": route.model},
    )
    db.add(user_message)
    await db.flush()

    retrieved = await vector_index.retrieve(
        db,
        query=question,
        project_id=project.id,
        paper_id=paper.id if paper else None,
        limit=max_citations + 3,
    )
    answer_text, confidence, blocked_reason = _compose_grounded_answer(question, retrieved, max_citations=max_citations)
    grounded = blocked_reason is None
    claim_type = _detect_claim_type(question, grounded=grounded)
    answer_message = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role="assistant",
        content=answer_text,
        claim_type=claim_type,
        confidence=confidence,
        grounded=grounded,
        metadata_json={
            "route": route.__dict__,
            "blocked_reason": blocked_reason,
            "retrieval_trace": [
                {
                    "paper_chunk_id": str(item["paper_chunk_id"]),
                    "rank": item.get("rank"),
                    "final_score": float(item.get("final_score") or item.get("score") or 0.0),
                    "rerank_score": float(item.get("rerank_score") or 0.0),
                    "trace": item.get("retrieval_trace", {}),
                }
                for item in retrieved
            ],
        },
    )
    db.add(answer_message)
    await db.flush()

    citations: list[dict] = []
    for rank, item in enumerate(retrieved[:max_citations], start=1):
        db.add(
            RetrievedChunk(
                message_id=answer_message.id,
                paper_chunk_id=item.get("paper_chunk_id"),
                rank=rank,
                score=float(item.get("final_score") or item.get("score") or 0.0),
                page_number=item.get("page_number"),
                locator=item.get("locator"),
                quoted_text=str(item.get("quoted_text") or ""),
            )
        )
        db.add(
            AnswerCitation(
                message_id=answer_message.id,
                paper_id=item["paper_id"],
                paper_chunk_id=item.get("paper_chunk_id"),
                page_number=item.get("page_number"),
                locator=item.get("locator"),
                quoted_text=str(item.get("quoted_text") or "")[:500],
            )
        )
        citations.append(
            {
                "paper_id": item["paper_id"],
                "page": item.get("page_number"),
                "locator": item.get("locator"),
                "quoted_text": str(item.get("quoted_text") or "")[:500],
            }
        )

    await db.commit()

    response = {
        "session_id": session.id,
        "answer": answer_text,
        "claim_type": answer_message.claim_type,
        "confidence": answer_message.confidence,
        "grounded": grounded,
        "citations": citations,
        "blocked_reason": blocked_reason,
    }
    if settings.CHAT_ENABLE_INTERNAL_DEBUG:
        response["retrieval_debug"] = answer_message.metadata_json.get("retrieval_trace", [])
    return response


async def get_session(db: AsyncSession, *, session_id: UUID, user: User) -> ChatSession | None:
    stmt = (
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == user.id)
        .options(
            selectinload(ChatSession.messages).selectinload(ChatMessage.answer_citations),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def add_highlight(
    db: AsyncSession,
    *,
    paper: Paper,
    user: User,
    color: str,
    note_text: str | None,
    quoted_text: str | None,
    locator: dict | None,
) -> PaperHighlight:
    highlight = PaperHighlight(
        paper_id=paper.id,
        user_id=user.id,
        color=color,
        note_text=note_text,
        quoted_text=quoted_text,
        locator=locator,
    )
    db.add(highlight)
    await db.commit()
    await db.refresh(highlight)
    return highlight

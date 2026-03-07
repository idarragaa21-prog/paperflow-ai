from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.metrics import chat_blocked_answers_total, chat_grounded_answers_total
from app.models.chat import AnswerCitation, ChatMessage, ChatSession, PaperHighlight, RetrievedChunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.services.llm.provider_adapters import OllamaAdapter, OpenClawChatAdapter
from app.services.model_router import resolve_model
from app.services.vector_index import vector_index

PROMPT_VERSION = "chat_v2_grounded_json"


def _normalized_claim_type(value: str | None, *, grounded: bool) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in {"dato", "resumen", "inferencia"}:
        return "resumen" if grounded else "dato"
    if settings.CHAT_DEFAULT_MODE == "extractive_strict" and normalized == "inferencia":
        return "resumen"
    return normalized


def _build_retrieval_trace(retrieved: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "paper_chunk_id": str(item["paper_chunk_id"]),
            "rank": item.get("rank"),
            "final_score": float(item.get("final_score") or item.get("score") or 0.0),
            "rerank_score": float(item.get("rerank_score") or 0.0),
            "trace": item.get("retrieval_trace", {}),
        }
        for item in retrieved
    ]


def _grounding_score(retrieved: list[dict[str, Any]], *, max_citations: int) -> float:
    strong_hits = [float(item.get("final_score") or item.get("score") or 0.0) for item in retrieved[:max_citations]]
    if not strong_hits:
        return 0.0
    return max(0.0, min(1.0, sum(strong_hits) / max(len(strong_hits), 1)))


def _block_response(retrieved: list[dict[str, Any]]) -> tuple[str, float, str]:
    del retrieved
    return (
        "No hay soporte documental suficiente para responder en modo evidence-based. Amplia la selección o procesa mejor el PDF.",
        0.0,
        "insufficient_grounding",
    )


def _build_messages(question: str, retrieved: list[dict[str, Any]], *, max_citations: int) -> tuple[str, str]:
    evidence_lines = []
    for index, item in enumerate(retrieved[:max_citations], start=1):
        evidence_lines.append(
            "\n".join(
                [
                    f"[Evidence {index}]",
                    f"paper_id: {item['paper_id']}",
                    f"page: {item.get('page_number')}",
                    f"locator: {json.dumps(item.get('locator') or {}, ensure_ascii=False)}",
                    f"score: {float(item.get('final_score') or item.get('score') or 0.0):.4f}",
                    f"quote: {str(item.get('quoted_text') or '')[:1200]}",
                ]
            )
        )
    system = (
        "You are PaperFlow AI in extractive evidence mode. "
        "Use only the supplied evidence. "
        "If the evidence is insufficient, answer with a short refusal and set blocked_reason. "
        "Return JSON only with keys: answer, claim_type, confidence, blocked_reason."
    )
    user = "\n\n".join(
        [
            f"Question:\n{question}",
            "Evidence:\n" + "\n\n".join(evidence_lines),
            (
                "Rules:\n"
                "- claim_type must be one of dato, resumen, inferencia.\n"
                "- In extractive_strict mode inferencia is forbidden; use resumen instead.\n"
                "- confidence must be a number between 0 and 1.\n"
                "- blocked_reason must be null unless evidence is insufficient.\n"
                "- Keep answer concise and grounded."
            ),
        ]
    )
    return system, user


def _adapter_for_route(route) -> OllamaAdapter | OpenClawChatAdapter:
    if route.provider == "ollama":
        return OllamaAdapter(route.model, base_url=settings.OLLAMA_BASE_URL)
    return OpenClawChatAdapter(route.model)


def _parse_model_json(raw_text: str) -> dict[str, Any]:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def _generate_grounded_answer(
    *,
    question: str,
    retrieved: list[dict[str, Any]],
    route,
    max_citations: int,
) -> tuple[str, float, str, str, float]:
    strong_hits = [item for item in retrieved if float(item.get("final_score") or item.get("score") or 0.0) >= settings.CHAT_MIN_GROUNDED_SCORE]
    if len(strong_hits) < settings.CHAT_MIN_RETRIEVED_CHUNKS:
        answer, confidence, blocked_reason = _block_response(retrieved)
        return answer, confidence, "dato", blocked_reason, 0.0

    system, user = _build_messages(question, strong_hits, max_citations=max_citations)
    adapter = _adapter_for_route(route)
    try:
        response = await adapter.complete(
            prompt=user,
            system=system,
            temperature=0.1,
            max_tokens=1000,
            json_mode=True,
        )
        payload = _parse_model_json(response.text)
    except Exception:
        answer, confidence, blocked_reason = _block_response(retrieved)
        return answer, confidence, "dato", "generation_unavailable", 0.0
    grounding_score = _grounding_score(strong_hits, max_citations=max_citations)
    model_confidence = float(payload.get("confidence") or 0.0)
    if model_confidence > 1:
        model_confidence = model_confidence / 100.0
    confidence = max(0.0, min(0.99, (grounding_score * 0.65) + (model_confidence * 0.35)))
    answer = str(payload.get("answer") or "").strip()
    blocked_reason = payload.get("blocked_reason")
    claim_type = _normalized_claim_type(str(payload.get("claim_type") or "resumen"), grounded=blocked_reason is None)
    if not answer:
        answer = "No se pudo generar una respuesta grounded."
        blocked_reason = blocked_reason or "empty_model_response"
        confidence = 0.0
    return answer, confidence, claim_type, blocked_reason, grounding_score


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

    answer_text, confidence, claim_type, blocked_reason, grounding_score = await _generate_grounded_answer(
        question=question,
        retrieved=retrieved,
        route=route,
        max_citations=max_citations,
    )
    grounded = blocked_reason is None
    retrieval_trace = _build_retrieval_trace(retrieved)
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
            "retrieval_trace": retrieval_trace,
            "model_name": route.model,
            "prompt_version": PROMPT_VERSION,
            "grounding_score": grounding_score,
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
    if grounded:
        chat_grounded_answers_total.inc()
    else:
        chat_blocked_answers_total.inc()

    response = {
        "session_id": session.id,
        "answer": answer_text,
        "claim_type": answer_message.claim_type,
        "confidence": answer_message.confidence,
        "grounded": grounded,
        "citations": citations,
        "blocked_reason": blocked_reason,
        "model_name": route.model,
        "grounding_score": grounding_score,
    }
    if settings.CHAT_ENABLE_INTERNAL_DEBUG:
        response["retrieval_debug"] = retrieval_trace
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

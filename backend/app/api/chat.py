from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatSessionResponse, HighlightCreate
from app.services.chat_service import add_highlight, ask, get_session
from app.services.permissions import require_paper_access, require_project_access
from app.services.vector_index import vector_index

router = APIRouter(tags=["chat"])

@router.post("/papers/{paper_id}/chat", response_model=ChatResponse)
async def chat_with_paper(
    paper_id: UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper, _membership = await require_paper_access(db, paper_id=paper_id, user=user, required_role="viewer")
    project, _project_membership = await require_project_access(db, project_id=paper.project_id, user=user, required_role="viewer")
    await vector_index.index_paper(db, paper_id=paper.id)
    result = await ask(
        db,
        project=project,
        paper=paper,
        user=user,
        question=payload.question,
        session_id=payload.session_id,
        task_type=payload.task_type,
        max_citations=payload.max_citations,
    )
    return ChatResponse(**result)


@router.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat_with_project(
    project_id: UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project, _membership = await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await ask(
        db,
        project=project,
        paper=None,
        user=user,
        question=payload.question,
        session_id=payload.session_id,
        task_type=payload.task_type,
        max_citations=payload.max_citations,
    )
    return ChatResponse(**result)


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = await get_session(db, session_id=session_id, user=user)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    messages = []
    for message in session.messages:
        messages.append(
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "claim_type": message.claim_type,
                "confidence": message.confidence,
                "grounded": message.grounded,
                "created_at": message.created_at.isoformat() if message.created_at else None,
                "citations": [
                    {
                        "paper_id": citation.paper_id,
                        "page": citation.page_number,
                        "locator": citation.locator,
                        "quoted_text": citation.quoted_text,
                    }
                    for citation in message.answer_citations
                ],
            }
        )
    return ChatSessionResponse(
        id=session.id,
        project_id=session.project_id,
        paper_id=session.paper_id,
        title=session.title,
        runtime_mode=session.runtime_mode,
        grounded=session.grounded,
        messages=messages,
    )


@router.post("/papers/{paper_id}/highlights")
async def create_highlight(
    paper_id: UUID,
    payload: HighlightCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper, _membership = await require_paper_access(db, paper_id=paper_id, user=user, required_role="viewer")
    highlight = await add_highlight(
        db,
        paper=paper,
        user=user,
        color=payload.color,
        note_text=payload.note_text,
        quoted_text=payload.quoted_text,
        locator=payload.locator,
    )
    return {
        "id": str(highlight.id),
        "paper_id": str(highlight.paper_id),
        "color": highlight.color,
        "note_text": highlight.note_text,
        "locator": highlight.locator,
    }

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.screening import EligibilityReason, PeerReviewAction, ProjectComment, ReviewFlow, ScreeningBatch, ScreeningDecision
from app.models.user import User
from app.schemas.screening import (
    EligibilityReasonCreate,
    EligibilityReasonResponse,
    PeerReviewActionPatch,
    PeerReviewActionResponse,
    PeerReviewActionCreate,
    ProjectCommentResponse,
    ProjectCommentCreate,
    ScreeningBatchCreate,
    ScreeningBatchResponse,
    ScreeningDecisionCreate,
    ScreeningDecisionResponse,
)
from app.services.permissions import require_project_access

router = APIRouter(prefix="/screening", tags=["screening"])


@router.post("/batches", response_model=ScreeningBatchResponse)
async def create_batch(
    payload: ScreeningBatchCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    batch = ScreeningBatch(project_id=payload.project_id, title=payload.title, stage=payload.stage, status="active")
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return ScreeningBatchResponse(id=batch.id, project_id=batch.project_id, title=batch.title, stage=batch.stage, status=batch.status)


@router.get("/batches", response_model=list[ScreeningBatchResponse])
async def list_batches(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(select(ScreeningBatch).where(ScreeningBatch.project_id == project_id).order_by(ScreeningBatch.created_at.desc()))
    return [
        ScreeningBatchResponse(id=batch.id, project_id=batch.project_id, title=batch.title, stage=batch.stage, status=batch.status)
        for batch in result.scalars().all()
    ]


@router.post("/decisions", response_model=ScreeningDecisionResponse)
async def create_decision(
    payload: ScreeningDecisionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = await db.get(ScreeningBatch, payload.batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Screening batch not found")
    await require_project_access(db, project_id=batch.project_id, user=user, required_role="reviewer")
    decision = ScreeningDecision(
        batch_id=batch.id,
        paper_id=payload.paper_id,
        user_id=user.id,
        reason_id=payload.reason_id,
        decision=payload.decision,
        stage=payload.stage,
        notes=payload.notes,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return ScreeningDecisionResponse(
        id=decision.id,
        batch_id=decision.batch_id,
        paper_id=decision.paper_id,
        decision=decision.decision,
        stage=decision.stage,
        reason_id=decision.reason_id,
        notes=decision.notes,
    )


@router.get("/decisions", response_model=list[ScreeningDecisionResponse])
async def list_decisions(
    batch_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = await db.get(ScreeningBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Screening batch not found")
    await require_project_access(db, project_id=batch.project_id, user=user, required_role="viewer")
    result = await db.execute(select(ScreeningDecision).where(ScreeningDecision.batch_id == batch_id).order_by(ScreeningDecision.created_at.desc()))
    return [
        ScreeningDecisionResponse(
            id=item.id,
            batch_id=item.batch_id,
            paper_id=item.paper_id,
            decision=item.decision,
            stage=item.stage,
            reason_id=item.reason_id,
            notes=item.notes,
        )
        for item in result.scalars().all()
    ]


@router.post("/reasons", response_model=EligibilityReasonResponse)
async def create_reason(
    payload: EligibilityReasonCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="editor")
    reason = EligibilityReason(project_id=payload.project_id, code=payload.code, label=payload.label, description=payload.description)
    db.add(reason)
    await db.commit()
    await db.refresh(reason)
    return EligibilityReasonResponse(
        id=reason.id,
        project_id=reason.project_id,
        code=reason.code,
        label=reason.label,
        description=reason.description,
    )


@router.get("/reasons", response_model=list[EligibilityReasonResponse])
async def list_reasons(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(select(EligibilityReason).where(EligibilityReason.project_id == project_id).order_by(EligibilityReason.label.asc()))
    return [
        EligibilityReasonResponse(
            id=item.id,
            project_id=item.project_id,
            code=item.code,
            label=item.label,
            description=item.description,
        )
        for item in result.scalars().all()
    ]


@router.get("/prisma")
async def get_prisma_counts(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(
        select(ScreeningDecision.decision, func.count())
        .join(ScreeningBatch, ScreeningBatch.id == ScreeningDecision.batch_id)
        .where(ScreeningBatch.project_id == project_id)
        .group_by(ScreeningDecision.decision)
    )
    counts = {decision: int(total) for decision, total in result.all()}
    flow = ReviewFlow(
        project_id=project_id,
        title="Auto-generated PRISMA counts",
        status="active",
        config_json={"source": "screening_decisions"},
        prisma_counts_json=counts,
    )
    db.add(flow)
    await db.commit()
    return {"project_id": str(project_id), "counts": counts}


@router.post("/comments")
async def create_comment(
    payload: ProjectCommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="reviewer")
    comment = ProjectComment(
        project_id=payload.project_id,
        user_id=user.id,
        body=payload.body,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"id": str(comment.id), "body": comment.body, "target_type": comment.target_type, "target_id": comment.target_id}


@router.get("/comments", response_model=list[ProjectCommentResponse])
async def list_comments(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(select(ProjectComment).where(ProjectComment.project_id == project_id).order_by(ProjectComment.created_at.desc()))
    return [
        ProjectCommentResponse(
            id=item.id,
            project_id=item.project_id,
            user_id=item.user_id,
            body=item.body,
            target_type=item.target_type,
            target_id=item.target_id,
        )
        for item in result.scalars().all()
    ]


@router.post("/peer-review-actions")
async def create_peer_review_action(
    payload: PeerReviewActionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=payload.project_id, user=user, required_role="reviewer")
    action = PeerReviewAction(
        project_id=payload.project_id,
        user_id=user.id,
        action=payload.action,
        status=payload.status,
        payload_json=payload.payload_json,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return {"id": str(action.id), "action": action.action, "status": action.status, "payload_json": action.payload_json}


@router.get("/peer-review-actions", response_model=list[PeerReviewActionResponse])
async def list_peer_review_actions(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_project_access(db, project_id=project_id, user=user, required_role="viewer")
    result = await db.execute(
        select(PeerReviewAction).where(PeerReviewAction.project_id == project_id).order_by(PeerReviewAction.created_at.desc())
    )
    return [
        PeerReviewActionResponse(
            id=item.id,
            project_id=item.project_id,
            user_id=item.user_id,
            action=item.action,
            status=item.status,
            payload_json=item.payload_json,
        )
        for item in result.scalars().all()
    ]


@router.patch("/peer-review-actions/{action_id}", response_model=PeerReviewActionResponse)
async def patch_peer_review_action(
    action_id: UUID,
    payload: PeerReviewActionPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    action = await db.get(PeerReviewAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Peer review action not found")
    await require_project_access(db, project_id=action.project_id, user=user, required_role="reviewer")
    action.status = payload.status
    if payload.payload_json is not None:
        action.payload_json = payload.payload_json
    await db.commit()
    await db.refresh(action)
    return PeerReviewActionResponse(
        id=action.id,
        project_id=action.project_id,
        user_id=action.user_id,
        action=action.action,
        status=action.status,
        payload_json=action.payload_json,
    )

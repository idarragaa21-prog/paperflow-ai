from __future__ import annotations

import inspect
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import permission_denials_total
from app.models.membership import ProjectMembership
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User

ROLE_RANK = {
    "viewer": 10,
    "reviewer": 20,
    "editor": 30,
    "owner": 40,
}


def role_allows(actual_role: str, required_role: str) -> bool:
    return ROLE_RANK.get(actual_role, 0) >= ROLE_RANK.get(required_role, 0)


async def get_project_membership(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
) -> tuple[Project | None, ProjectMembership | None]:
    project = await db.get(Project, project_id)
    if project is None:
        return None, None

    if project.user_id == user_id:
        membership = ProjectMembership(project_id=project_id, user_id=user_id, role="owner")
        if hasattr(db, "add"):
            db.add(membership)
        flush = getattr(db, "flush", None)
        if callable(flush):
            maybe_coro = flush()
            if inspect.isawaitable(maybe_coro):
                await maybe_coro
        return project, membership

    result = await db.execute(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
        .where(ProjectMembership.user_id == user_id)
    )
    scalar_result = result.scalars()
    if hasattr(scalar_result, "first"):
        membership = scalar_result.first()
    else:
        items = scalar_result.all() if hasattr(scalar_result, "all") else []
        membership = items[0] if items else None
    return project, membership


async def require_project_access(
    db: AsyncSession,
    *,
    project_id: UUID,
    user: User,
    required_role: str = "viewer",
) -> tuple[Project, ProjectMembership]:
    project, membership = await get_project_membership(db, project_id=project_id, user_id=user.id)
    if project is None or membership is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not role_allows(membership.role, required_role):
        permission_denials_total.labels(resource="project", required_role=required_role).inc()
        raise HTTPException(status_code=403, detail="Insufficient project permissions")
    return project, membership


async def require_paper_access(
    db: AsyncSession,
    *,
    paper_id: UUID,
    user: User,
    required_role: str = "viewer",
) -> tuple[Paper, ProjectMembership]:
    paper = await db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    _, membership = await require_project_access(db, project_id=paper.project_id, user=user, required_role=required_role)
    return paper, membership


async def list_accessible_projects(db: AsyncSession, *, user: User) -> list[tuple[Project, str]]:
    result = await db.execute(
        select(Project, ProjectMembership.role)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id, isouter=True)
        .where(or_(Project.user_id == user.id, ProjectMembership.user_id == user.id))
        .order_by(Project.created_at.desc())
    )
    deduped: dict[UUID, tuple[Project, str]] = {}
    for project, role in result.all():
        effective_role = "owner" if project.user_id == user.id else (role or "viewer")
        previous = deduped.get(project.id)
        if previous is None or ROLE_RANK[effective_role] > ROLE_RANK.get(previous[1], 0):
            deduped[project.id] = (project, effective_role)
    return list(deduped.values())

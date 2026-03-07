from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.models.project import Project


class PaperRepository(Protocol):
    async def get_project(self, project_id: UUID) -> Project | None: ...

    async def get_paper(self, paper_id: UUID) -> Paper | None: ...

    async def find_duplicate_by_identifiers(
        self, *, project_id: UUID, pmid: str | None, doi: str | None
    ) -> Paper | None: ...

    async def find_duplicate_by_hash(self, *, project_id: UUID, content_hash: str) -> Paper | None: ...

    async def create_paper(self, paper: Paper) -> Paper: ...

    async def delete_paper(self, paper: Paper) -> None: ...


@dataclass
class SQLPaperRepository:
    db: AsyncSession

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self.db.get(Project, project_id)

    async def get_paper(self, paper_id: UUID) -> Paper | None:
        return await self.db.get(Paper, paper_id)

    async def find_duplicate_by_identifiers(
        self, *, project_id: UUID, pmid: str | None, doi: str | None
    ) -> Paper | None:
        if not pmid and not doi:
            return None

        clauses = []
        if pmid:
            clauses.append(Paper.pmid == pmid)
        if doi:
            clauses.append(Paper.doi == doi)

        q = await self.db.execute(select(Paper).where(Paper.project_id == project_id).where(or_(*clauses)))
        return q.scalars().first()

    async def find_duplicate_by_hash(self, *, project_id: UUID, content_hash: str) -> Paper | None:
        q = await self.db.execute(
            select(Paper).where(Paper.project_id == project_id).where(Paper.content_hash == content_hash)
        )
        return q.scalars().first()

    async def create_paper(self, paper: Paper) -> Paper:
        self.db.add(paper)
        await self.db.commit()
        await self.db.refresh(paper)
        return paper

    async def delete_paper(self, paper: Paper) -> None:
        await self.db.delete(paper)
        await self.db.commit()

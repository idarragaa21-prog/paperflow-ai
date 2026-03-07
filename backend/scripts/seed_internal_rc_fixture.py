from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func, select

from app.core.security import hash_password
from app.database import async_session_maker
from app.models.membership import ProjectMembership
from app.models.paper import Paper
from app.models.project import Project
from app.models.reference_item import ReferenceItem
from app.models.screening import EligibilityReason, PeerReviewAction, ProjectComment, ScreeningBatch
from app.models.user import User
from app.models.document import PaperChunk, PaperCitationSpan, PaperParseRun
from app.services.extraction_service import create_extraction_record


def _paper_text(index: int) -> str:
    return (
        f"Study {index + 1} investigated remote monitoring in a synthetic internal RC fixture. "
        f"The main finding was that intervention cohort {index + 1} reduced preventable admissions and improved follow-up adherence. "
        f"Outcome measures included pain, function, utilization and readmission risk. "
        f"Conclusion: the seeded evidence supports a positive effect size for reproducible chat, extraction and screening workflows."
    )


async def _ensure_user(session, *, email: str, password: str, full_name: str) -> User:
    result = await session.execute(select(User).where(User.email == email).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, password_hash=hash_password(password), full_name=full_name, is_active=True)
        session.add(user)
        await session.flush()
    else:
        user.password_hash = hash_password(password)
        user.full_name = full_name
        user.is_active = True
    return user


async def _ensure_project(session, *, owner: User, title: str) -> Project:
    result = await session.execute(
        select(Project).where(Project.user_id == owner.id).where(Project.title == title).limit(1)
    )
    project = result.scalar_one_or_none()
    if project is None:
        project = Project(user_id=owner.id, title=title, description="Seeded Internal RC fixture", runtime_mode="local_only")
        session.add(project)
        await session.flush()
    return project


async def _ensure_membership(session, *, project_id: UUID, user_id: UUID, role: str) -> None:
    result = await session.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id).where(ProjectMembership.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        session.add(ProjectMembership(project_id=project_id, user_id=user_id, role=role))
    else:
        membership.role = role


def _content_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


async def _seed_papers(session, *, project: Project, target_count: int) -> list[Paper]:
    result = await session.execute(select(Paper).where(Paper.project_id == project.id).order_by(Paper.created_at.asc()))
    papers = list(result.scalars().all())
    for index in range(len(papers), target_count):
        text = _paper_text(index)
        paper = Paper(
            project_id=project.id,
            title=f"Internal RC Synthetic Study {index + 1}",
            authors="PaperFlow Fixture Team",
            doi=f"10.4242/paperflow.rc.{index + 1:04d}",
            pmid=f"{900000 + index + 1}",
            journal="PaperFlow Internal Journal",
            publication_year=2024 - (index % 5),
            language="en",
            abstract_text=text[:240],
            filename=f"fixture-paper-{index + 1}.pdf",
            file_path=f"seeded/fixture-paper-{index + 1}.pdf",
            file_size_kb=128,
            content_hash=_content_hash(f"{project.id}:{index}:{text}"),
            source_provider="seed_fixture",
            source_type="seeded",
            is_open_access=True,
            oa_url=f"https://example.org/fixture/{index + 1}.pdf",
            favorite=index == 0,
            tags=["fixture", "internal_rc"],
            is_processed=True,
            full_text_extracted=text,
            processing_status="parsed",
        )
        session.add(paper)
        await session.flush()

        parse_run = PaperParseRun(
            paper_id=paper.id,
            status="completed",
            parser_name="fixture_seed",
            parser_version="1",
            used_ocr=False,
            pages_count=1,
            chars_extracted=len(text),
            warnings=[],
            metadata_json={
                "used_ocr": False,
                "grobid_status": "seeded",
                "parse_warnings": [],
                "failure_class": None,
                "pages": [{"page_number": 1, "text": text}],
                "blocks": [{"page": 1, "text": text, "bbox": [0, 0, 100, 100]}],
                "tables": [],
                "figures": [],
                "citations": [{"label": f"[{index + 1}]", "page_number": 1}],
                "tei_xml": "<TEI>fixture</TEI>",
            },
        )
        session.add(parse_run)
        await session.flush()

        locator = {"page": 1, "char_start": 0, "char_end": min(len(text), 220), "bbox": [0, 0, 100, 100]}
        session.add(
            PaperChunk(
                paper_id=paper.id,
                parse_run_id=parse_run.id,
                page_number=1,
                chunk_index=0,
                text=text,
                token_count=len(text.split()),
                locator=locator,
                source_type="body",
            )
        )
        session.add(
            PaperCitationSpan(
                paper_id=paper.id,
                parse_run_id=parse_run.id,
                page_number=1,
                label=f"[{index + 1}]",
                locator=locator,
                quoted_text=text[:220],
            )
        )
        papers.append(paper)
    await session.commit()
    return papers


async def _seed_references(session, *, project: Project, papers: list[Paper], limit: int = 24) -> None:
    result = await session.execute(select(func.count()).select_from(ReferenceItem).where(ReferenceItem.project_id == project.id))
    existing = int(result.scalar_one() or 0)
    if existing >= min(limit, len(papers)):
        return
    for paper in papers[existing:limit]:
        session.add(
            ReferenceItem(
                project_id=project.id,
                paper_id=paper.id,
                source_format="seeded",
                citation_key=f"fixture{paper.publication_year or 2024}{paper.id.hex[:6]}",
                title=paper.title,
                authors=["PaperFlow Fixture Team"],
                journal=paper.journal,
                publication_year=paper.publication_year,
                doi=paper.doi,
                pmid=paper.pmid,
                abstract_text=paper.abstract_text,
                language=paper.language,
                raw_payload={"seeded": True},
            )
        )
    await session.commit()


async def _seed_screening(session, *, project: Project, owner: User, reviewer: User, first_paper: Paper) -> None:
    batch = (
        await session.execute(select(ScreeningBatch).where(ScreeningBatch.project_id == project.id).limit(1))
    ).scalar_one_or_none()
    if batch is None:
        batch = ScreeningBatch(project_id=project.id, title="Internal RC Batch", stage="title_abstract", status="active")
        session.add(batch)
    reason = (
        await session.execute(select(EligibilityReason).where(EligibilityReason.project_id == project.id).limit(1))
    ).scalar_one_or_none()
    if reason is None:
        reason = EligibilityReason(project_id=project.id, code="wrong_population", label="Wrong population")
        session.add(reason)
    comment = (
        await session.execute(select(ProjectComment).where(ProjectComment.project_id == project.id).limit(1))
    ).scalar_one_or_none()
    if comment is None:
        session.add(
            ProjectComment(
                project_id=project.id,
                user_id=reviewer.id,
                body="Seeded reviewer note for internal RC validation.",
                target_type="paper",
                target_id=str(first_paper.id),
            )
        )
    action = (
        await session.execute(select(PeerReviewAction).where(PeerReviewAction.project_id == project.id).limit(1))
    ).scalar_one_or_none()
    if action is None:
        session.add(
            PeerReviewAction(
                project_id=project.id,
                user_id=reviewer.id,
                action="screening_review",
                status="open",
                payload_json={"paper_id": str(first_paper.id)},
            )
        )
    await session.commit()


async def _seed_extraction(session, *, project: Project, paper: Paper) -> None:
    from app.models.extraction import ExtractionRecord

    existing = await session.execute(
        select(ExtractionRecord).where(ExtractionRecord.project_id == project.id).where(ExtractionRecord.paper_id == paper.id).limit(1)
    )
    if existing.scalar_one_or_none() is None:
        await create_extraction_record(session, project_id=project.id, paper_id=paper.id, template_id=None)


async def _run(args) -> dict:
    async with async_session_maker() as session:
        owner = await _ensure_user(session, email=args.owner_email, password=args.owner_password, full_name="RC Owner")
        reviewer = await _ensure_user(session, email=args.reviewer_email, password=args.reviewer_password, full_name="RC Reviewer")
        await session.commit()

        project = await _ensure_project(session, owner=owner, title=args.project_title)
        await _ensure_membership(session, project_id=project.id, user_id=owner.id, role="owner")
        await _ensure_membership(session, project_id=project.id, user_id=reviewer.id, role="reviewer")
        await session.commit()

        papers = await _seed_papers(session, project=project, target_count=args.paper_count)
        await _seed_references(session, project=project, papers=papers)
        await _seed_screening(session, project=project, owner=owner, reviewer=reviewer, first_paper=papers[0])
        await _seed_extraction(session, project=project, paper=papers[0])

        fixture = {
            "owner": {"id": str(owner.id), "email": owner.email, "password": args.owner_password},
            "reviewer": {"id": str(reviewer.id), "email": reviewer.email, "password": args.reviewer_password},
            "project": {"id": str(project.id), "title": project.title},
            "papers": {"count": len(papers), "first_paper_id": str(papers[0].id)},
        }
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
        print(json.dumps(fixture, indent=2))
        return fixture


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an internal RC fixture for Playwright/load tests.")
    parser.add_argument("--output", default=str(BACKEND_ROOT.parent / "tmp" / "internal_rc_fixture.json"))
    parser.add_argument("--project-title", default="Internal RC Fixture")
    parser.add_argument("--paper-count", type=int, default=500)
    parser.add_argument("--owner-email", default="rc-owner@paperflow.local")
    parser.add_argument("--owner-password", default="paperflow-e2e-123")
    parser.add_argument("--reviewer-email", default="rc-reviewer@paperflow.local")
    parser.add_argument("--reviewer-password", default="paperflow-e2e-123")
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

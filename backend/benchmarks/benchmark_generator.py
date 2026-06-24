import asyncio
import time

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base
from app.models.project import Project
from app.models.paper import Paper
from app.models.note import Note
from app.models.user import User
from app.services.clinical.generator import _collect_project_papers

async def run_benchmark():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        user = User(email="test@example.com", password_hash="hash")
        session.add(user)
        await session.flush()

        project = Project(user_id=user.id, name="Test Project")
        session.add(project)
        await session.flush()

        papers = []
        for i in range(50):
            p = Paper(
                project_id=project.id,
                title=f"Test paper {i}",
                full_text_extracted="This is a test paper full text"
            )
            session.add(p)
            papers.append(p)

        await session.flush()

        for p in papers:
            for j in range(3):
                note = Note(
                    project_id=project.id,
                    paper_id=p.id,
                    title=f"Note {j}",
                    content=f"Summary content {j}",
                    note_type="summary"
                )
                session.add(note)

        await session.commit()

        # Warmup
        await _collect_project_papers(session, project.id, "test", max_papers=20)

        start = time.perf_counter()
        for _ in range(10):
            await _collect_project_papers(session, project.id, "test", max_papers=20)

        elapsed = time.perf_counter() - start
        print(f"BASELINE: Benchmark completed in {elapsed:.4f} seconds (average {elapsed/10:.4f}s per call)")

if __name__ == "__main__":
    asyncio.run(run_benchmark())

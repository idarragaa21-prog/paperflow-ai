import asyncio
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Setup simple models instead to test logic and test sqlite compatibility
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, ForeignKey

class Base(DeclarativeBase):
    pass

class Paper(Base):
    __tablename__ = 'papers'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)

class SearchResult(Base):
    __tablename__ = 'search_results'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey('papers.id'))
    abstract: Mapped[str] = mapped_column(String)

class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey('papers.id'))
    content: Mapped[str] = mapped_column(String)
    note_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer)

async def simulate_collect(session, max_papers=10):
    papers = (await session.execute(select(Paper))).scalars().all()

    out = []
    # simulate the loop
    for p in papers[:max_papers]:
        qn = await session.execute(
            select(Note)
            .where(Note.paper_id == p.id, Note.note_type == "summary")
            .order_by(Note.created_at.desc())
            .limit(1)
        )
        note = qn.scalar_one_or_none()

        out.append({
            "paper_id": p.id,
            "title": p.title,
            "summary_note": note.content if note else None,
        })
    return out

async def simulate_collect_optimized(session, max_papers=10):
    papers = (await session.execute(select(Paper))).scalars().all()
    papers = papers[:max_papers]

    out = []
    if not papers:
        return out

    paper_ids = [p.id for p in papers]

    # In a real solution, we could use window functions like row_number(),
    # but sqlite/sqlalchemy might have issues, or we can just fetch all notes
    # for these papers and group them in python.
    # Here we simulate fetching the latest notes.
    qn = await session.execute(
        select(Note)
        .where(Note.paper_id.in_(paper_ids), Note.note_type == "summary")
        .order_by(Note.paper_id, Note.created_at.desc())
    )
    notes = qn.scalars().all()

    notes_by_paper = {}
    for n in notes:
        if n.paper_id not in notes_by_paper:
            notes_by_paper[n.paper_id] = n

    for p in papers:
        note = notes_by_paper.get(p.id)
        out.append({
            "paper_id": p.id,
            "title": p.title,
            "summary_note": note.content if note else None,
        })

    return out

async def run():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for i in range(100):
            p = Paper(title=f"Paper {i}")
            session.add(p)
            await session.flush()
            for j in range(5):
                n = Note(paper_id=p.id, content=f"Content {j}", note_type="summary", created_at=j)
                session.add(n)
        await session.commit()

        # Benchmark unoptimized
        t0 = time.perf_counter()
        for _ in range(100):
            await simulate_collect(session, max_papers=50)
        t1 = time.perf_counter()
        print(f"Unoptimized time: {t1-t0:.4f}s")

        # Benchmark optimized
        t0 = time.perf_counter()
        for _ in range(100):
            await simulate_collect_optimized(session, max_papers=50)
        t1 = time.perf_counter()
        print(f"Optimized time: {t1-t0:.4f}s")

if __name__ == "__main__":
    asyncio.run(run())

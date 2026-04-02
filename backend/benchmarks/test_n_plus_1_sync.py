import time
from sqlalchemy import create_engine, select, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

class Base(DeclarativeBase):
    pass

class Paper(Base):
    __tablename__ = 'papers'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)

class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey('papers.id'))
    content: Mapped[str] = mapped_column(String)
    note_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer)

def simulate_collect(session, max_papers=10):
    papers = session.execute(select(Paper)).scalars().all()

    out = []
    for p in papers[:max_papers]:
        qn = session.execute(
            select(Note)
            .where(Note.paper_id == p.id, Note.note_type == "summary")
            .order_by(Note.created_at.desc())
            .limit(1)
        )
        note = qn.scalar_one_or_none()
        out.append({"id": p.id, "note": note.content if note else None})
    return out

def simulate_collect_optimized(session, max_papers=10):
    papers = session.execute(select(Paper)).scalars().all()[:max_papers]

    out = []
    if not papers:
        return out

    paper_ids = [p.id for p in papers]

    qn = session.execute(
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
        out.append({"id": p.id, "note": note.content if note else None})
    return out

def run():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        for i in range(100):
            p = Paper(title=f"Paper {i}")
            session.add(p)
            session.flush()
            for j in range(5):
                n = Note(paper_id=p.id, content=f"Content {j}", note_type="summary", created_at=j)
                session.add(n)
        session.commit()

        t0 = time.perf_counter()
        for _ in range(100):
            simulate_collect(session, max_papers=50)
        t1 = time.perf_counter()
        print(f"Unoptimized time: {t1-t0:.4f}s")

        t0 = time.perf_counter()
        for _ in range(100):
            simulate_collect_optimized(session, max_papers=50)
        t1 = time.perf_counter()
        print(f"Optimized time: {t1-t0:.4f}s")

if __name__ == "__main__":
    run()

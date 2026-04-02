import re

with open("backend/app/workers/tasks.py", "r") as f:
    content = f.read()

# First block:
block1 = """<<<<<<< Updated upstream
                for pid in paper_ids:
                    p_uuid = UUID(pid)
                    paper = papers_map.get(p_uuid)
=======
                for pid in params.paper_ids:
                    paper = await db.get(Paper, UUID(pid))
>>>>>>> Stashed changes"""

rep1 = """                for pid in params.paper_ids:
                    p_uuid = UUID(pid)
                    paper = papers_map.get(p_uuid)"""

content = content.replace(block1, rep1)

# Second block:
block2 = """<<<<<<< Updated upstream
                insert_vals = [
                    {"presentation_id": presentation.id, "paper_id": UUID(pid)}
                    for pid in paper_ids
                    if UUID(pid) in papers_map
                ]
                if insert_vals:
                    await db.execute(presentation_papers.insert().values(insert_vals))
=======
                for pid in params.paper_ids:
                    paper_uuid = UUID(pid)
                    paper_obj = await db.get(Paper, paper_uuid)
                    if not paper_obj:
                        continue
                    await db.execute(
                        presentation_papers.insert().values(presentation_id=presentation.id, paper_id=paper_uuid)
                    )
>>>>>>> Stashed changes"""

rep2 = """                insert_vals = [
                    {"presentation_id": presentation.id, "paper_id": UUID(pid)}
                    for pid in params.paper_ids
                    if UUID(pid) in papers_map
                ]
                if insert_vals:
                    await db.execute(presentation_papers.insert().values(insert_vals))"""

content = content.replace(block2, rep2)

with open("backend/app/workers/tasks.py", "w") as f:
    f.write(content)

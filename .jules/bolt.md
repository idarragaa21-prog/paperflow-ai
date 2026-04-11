
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-30 - N+1 query resolved in presentation generation
**Learning:** Found an N+1 query pattern in `backend/app/api/presentations.py` where updating/creating a presentation fetched each `Paper` one by one using `db.get()`. This could make up to 10 separate database calls for a single presentation creation endpoint.
**Action:** Replaced the loop with a single `db.execute(select(Paper).where(Paper.id.in_(payload.paper_ids)))` to fetch all selected papers at once, reducing latency and DB load.

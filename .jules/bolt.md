
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-23 - N+1 Query in Presentations Endpoint
**Learning:** Found an N+1 query in `app/api/presentations.py` where paper metadata was fetched sequentially within a loop when generating presentations for up to 10 papers. This pattern mirrors previous N+1 issues and proves they exist across endpoints accepting batched lists of IDs.
**Action:** Replaced the loop-based sequential `db.get` calls with a batched `db.execute(select(Paper).where(Paper.id.in_(payload.paper_ids)))` operation and an O(1) in-memory dictionary lookup. Always check endpoints that accept arrays of UUIDs for this anti-pattern.

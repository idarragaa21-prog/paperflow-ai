
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-18 - N+1 query resolved in presentation creation
**Learning:** In endpoint validation loops, using `await db.get(Model, id)` per item creates an O(n) N+1 query problem, which severely impacts creation endpoints that validate multiple relationships.
**Action:** Always batch fetch dependencies in validation layers using `await db.execute(select(Model).where(Model.id.in_(item_ids)))` and map them to dictionaries for efficient O(1) in-memory checks.


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - Batch processing in loops risks iterator exhaustion
**Learning:** When batching an array of items with a list comprehension (`[chunk.text for chunk in chunks]`) before running a `zip(chunks, vectors)` on them, be highly aware that if `chunks` is a generator or exhausted iterator rather than a materialized list, the list comprehension will exhaust it completely. This will silently cause the subsequent `zip` to yield nothing and silently drop all database points without any errors. While `chunks` in this case was an already materialized list (`chunks_q.scalars().all()`), it is a critical pattern to watch out for.
**Action:** When working with chunks or lists returned from `db.execute().scalars()` in loops, always verify whether they are iterables or fully materialized lists before refactoring to batch processing patterns, to prevent silent data drop bugs.

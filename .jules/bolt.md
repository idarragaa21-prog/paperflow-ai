
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-06 - Optimized batch upload N+1 query and memory
**Learning:** Found N+1 query in create_batch loop and heavy memory usage from accumulating await f.read().
**Action:** Pre-calculated hashes and fetched existing papers with in_() in a single query. Used await f.seek(0) after read() to avoid memory regression, and updated local dictionary for intra-batch duplicates.

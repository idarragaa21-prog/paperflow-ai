
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## $(date +%Y-%m-%d) - N+1 API call bottleneck in indexing
**Learning:** Vectorizing texts individually during chunk indexing can cause a significant bottleneck due to multiple network calls to the model. Batched vectorization should be used instead.
**Action:** Use batched API calls for embedding texts when processing lists of chunks.

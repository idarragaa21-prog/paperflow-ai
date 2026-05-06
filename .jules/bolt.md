
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-18 - Avoid N+1 requests in vector indexing
**Learning:** Embedding models require explicit consistency across batched and unbatched API calls. Replacing `_embed_text` loops with batched `_embed_texts` solves N+1 bottleneck, but both must strictly resolve to `settings.PAPERFLOW_EMBEDDING_MODEL`.
**Action:** Always verify batch vs single-item method implementations internally use the same base configuration prior to refactoring to batched processes.

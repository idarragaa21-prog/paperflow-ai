
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-29 - Prevent N+1 HTTP bottlenecks when embedding document chunks
**Learning:** Calling `_embed_text` in a loop when indexing document chunks results in N+1 HTTP request bottlenecks to the embedding service.
**Action:** Use the batched `_embed_texts` method to process multiple chunks in a single API call when handling lists of chunks in `index_paper` and similar bulk operations.

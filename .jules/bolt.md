
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-30 - Batch vector embedding calls
**Learning:** In the `index_paper` function of `backend/app/services/vector_index.py`, embedding each chunk inside a loop led to an N+1 HTTP request bottleneck because `_embed_text` performs a separate API call for each chunk. Additionally, when using `_embed_texts` (the batching method), `settings.PAPERFLOW_CHAT_MODEL` was being used incorrectly instead of `settings.PAPERFLOW_EMBEDDING_MODEL`, leading to potentially inconsistent vector dimensions or spaces.
**Action:** Always prefer batched operations (`_embed_texts`) when processing a collection of inputs (like paper chunks) to minimize HTTP overhead. Ensure consistent model usage (e.g., `PAPERFLOW_EMBEDDING_MODEL`) across both single and batched embedding functions.

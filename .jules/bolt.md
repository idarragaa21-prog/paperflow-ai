
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-24 - Fix N+1 embedding request bottleneck
**Learning:** Embedding chunks sequentially during paper indexing causes a massive N+1 HTTP request bottleneck, slowing down ingestion. Additionally, batch embedding functions must use the exact same embedding model (not the chat model) as single-text embedding to ensure semantic vector spaces align.
**Action:** Always batch texts into a single list and use the batch endpoint (`_embed_texts`) when processing multiple documents/chunks. Consistently verify that the correct model identifier (e.g. `PAPERFLOW_EMBEDDING_MODEL`) is applied across all embedding endpoints.

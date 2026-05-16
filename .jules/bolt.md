
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-16 - Batching embeddings to avoid N+1 requests over HTTP
**Learning:** The `index_paper` method was making individual HTTP requests to Ollama for each document chunk via `_embed_text` in a loop, causing an N+1 API call bottleneck.
**Action:** Replaced the loop with a single batched call using `_embed_texts` to process multiple chunks simultaneously. Also discovered that both single and batch embedding methods must use `settings.PAPERFLOW_EMBEDDING_MODEL` to ensure consistency.

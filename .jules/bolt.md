
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-20 - Batching Embeddings Avoids N+1 HTTP Bottleneck
**Learning:** Embedding chunks sequentially creates an N+1 HTTP request bottleneck, slowing down bulk indexing operations significantly due to network overhead.
**Action:** Always prefer batch embedding endpoints (`_embed_texts`) over single-item embedding endpoints (`_embed_text`) when processing lists of strings, to eliminate round-trip latency overhead.

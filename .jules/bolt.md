
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2025-02-12 - Fix N+1 HTTP bottleneck in vector indexing
**Learning:** Generating embeddings one chunk at a time using `_embed_text` in a loop causes significant performance degradation due to multiple sequential HTTP requests (N+1 problem).
**Action:** Always use batch embedding endpoints (like `_embed_texts`) to process multiple items in a single HTTP request whenever possible.

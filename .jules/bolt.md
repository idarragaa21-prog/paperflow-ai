
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2025-02-28 - N+1 HTTP Request resolved in embedding document chunks
**Learning:** Found an N+1 HTTP request pattern where `index_paper` embedded each paper chunk individually via `_embed_text`.
**Action:** Batched embedding calls using `_embed_texts` to reduce latency and API calls.

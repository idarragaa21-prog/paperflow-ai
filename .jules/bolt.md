
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-18 - N+1 HTTP request resolved in embedding chunks
**Learning:** Found an N+1 API call pattern in `index_paper` where `_embed_text` was called inside a loop over text chunks, resulting in multiple sequential HTTP requests to the embedding service.
**Action:** Utilize the `_embed_texts` batching function provided by the service and iterate over `zip(chunks, vectors)` to maintain order while severely reducing HTTP overhead.

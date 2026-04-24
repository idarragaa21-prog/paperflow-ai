
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-24 - N+1 HTTP Request in Vector Indexing
**Learning:** Calling the embedding API for each chunk in a loop (`_embed_text`) creates an N+1 HTTP request bottleneck when indexing papers, significantly slowing down the process. The service already had a batch method (`_embed_texts`) available.
**Action:** Replaced the loop with a single `_embed_texts` call to embed all chunks in one request before creating the index points.

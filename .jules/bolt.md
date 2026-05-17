
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-17 - N+1 API calls bottleneck in chunk embeddings
**Learning:** Sequential HTTP requests to external LLM API endpoints during indexing (N+1 pattern) create massive latency bottlenecks for large papers.
**Action:** Always utilize batch embedding endpoints (`_embed_texts`) for processing collections instead of looping over single-item embedding methods.


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2025-05-09 - Batch Embedding Optimization
**Learning:** N+1 calls to external services like Ollama for generating embeddings during document indexing can severely impact performance. Processing chunks individually with `_embed_text` blocks on network I/O for each document chunk.
**Action:** Use batched API calls (`_embed_texts`) when processing multiple items like document chunks. Gather the data first, make a single API request, and then process the results to significantly reduce overhead.


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-04-21 - N+1 HTTP Request Bottleneck in Document Chunk Embedding
**Learning:** Indexing document chunks to vector databases line-by-line introduces severe N+1 HTTP request bottlenecks when making local or remote Ollama requests via httpx. Although `_embed_texts` was available for batch processing, the iterative `for chunk in chunks` flow missed it.
**Action:** Always map entity batches (e.g., extracting just texts into an array) to use batch API endpoints before writing `for` loops in database seeding or indexing pipelines. Match outputs to inputs using `zip()` later in the logic.

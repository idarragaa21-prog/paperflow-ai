
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-15 - Batched embeddings for chunk indexing
**Learning:** Indexing large papers into Qdrant could cause an N+1 HTTP bottleneck because it sent each text chunk to `_embed_text` sequentially, which then hit the Ollama embedding API. `VectorIndex._embed_texts()` already existed to support bulk API calls, making this an easy performance win to reduce network latency during ingestion.
**Action:** When implementing any loop that makes API calls or database hits for single elements (e.g., chunk embeddings), always check if a plural/batch method (e.g., `_embed_texts`) exists on the same service to bundle those requests.

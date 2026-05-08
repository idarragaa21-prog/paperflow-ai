
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-08 - Batch HTTP Requests for Embeddings in Qdrant Vector Index
**Learning:** Found a classic N+1 HTTP request bottleneck in `backend/app/services/vector_index.py` during paper indexing. The `index_paper` method was iterating over all document chunks and calling the embedding API sequentially (`_embed_text`). This causes significant latency overhead per chunk.
**Action:** Always look for opportunities to batch API calls. Extracted all chunk texts, passed them as a single list to a batched `_embed_texts` method, and then zipped the original chunks with the resulting vectors to maintain mapping.

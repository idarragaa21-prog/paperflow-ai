
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-19 - N+1 embeddings in Vector Indexing
**Learning:** Found an N+1 performance bottleneck during paper indexing where `vector_index.py` extracted text embeddings by sending individual HTTP requests for each document chunk.
**Action:** Replaced the loop over chunks with a single batched call (`_embed_texts`) that sends all chunks to the embedding model in one HTTP request, reducing network latency and improving indexing performance.

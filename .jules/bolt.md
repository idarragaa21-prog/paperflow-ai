
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - Batching Embeddings to fix N+1 Bottleneck
**Learning:** Found an N+1 API bottleneck in `backend/app/services/vector_index.py` during Qdrant ingestion, where individual paper chunk texts were embedded one-by-one by calling `_embed_text`. Because papers have multiple chunks, this causes many sequential external API requests, delaying indexing.
**Action:** Replaced the loop containing `_embed_text(chunk.text)` with a list comprehension that extracts the texts and passes them all to `_embed_texts(chunk_texts)` in one API batch.

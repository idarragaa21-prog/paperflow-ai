
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-04 - Optimize document embeddings processing
**Learning:** The document embedding endpoint processes multiple elements simultaneously. Sending elements to `_embed_text` in a loop invokes an N+1 API request pattern, significantly hurting processing times.
**Action:** Used the batched `_embed_texts` method when looping text chunks to hit API embeddings en masse instead of serially over network iterations.

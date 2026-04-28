
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-04-28 - N+1 HTTP request resolved in batched embedding chunks
**Learning:** Found an N+1 performance bottleneck when iterating through text chunks and calling `_embed_text()` individually. This sends one HTTP request per chunk to the embedding API, which drastically increases latency during paper indexing.
**Action:** Used the batched API call `_embed_texts()` by mapping all chunk texts into a list first, making only one HTTP call, and then zipping the embedded results back with the chunks.

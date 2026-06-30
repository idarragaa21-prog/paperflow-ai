
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-30 - N+1 query resolved in batch uploads
**Learning:** Found a common N+1 query pattern where creating a batch of files iteratively checks the DB for duplicate content hashes.
**Action:** Pre-calculated hashes and fetched existing papers using a single `where(Paper.content_hash.in_(...))` query, using `await f.seek(0)` after reading to avoid accumulating memory, and updating the local dictionary with newly created items to catch intra-batch duplicates.

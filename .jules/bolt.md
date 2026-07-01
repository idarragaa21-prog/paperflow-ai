
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2025-02-17 - Prevent N+1 queries in batch uploads
**Learning:** Found a performance bottleneck where uploading a batch of PDF files caused an N+1 query problem by doing `db.execute` checks for each file's hash in a loop. Memory regression could also happen if `await f.seek(0)` wasn't used after reading.
**Action:** Pre-calculate all hashes, use a single query with `.in_()` to fetch existing models, and update a dictionary with newly created objects within the loop to correctly handle intra-batch duplicates.

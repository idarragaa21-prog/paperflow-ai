
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-07-06 - N+1 query resolved in batch uploads
**Learning:** Found a common N+1 query pattern where batch file uploads in `create_batch` fetched each existing paper one by one using `db.execute()`. Pre-calculating hashes and avoiding memory regressions using `await f.seek(0)` after reading is critical before the single query.
**Action:** Used `in_()` on an array of file hashes to fetch all records in a single query, mapped them in memory, and updated the dictionary with newly created objects within the loop to handle intra-batch duplicates correctly.

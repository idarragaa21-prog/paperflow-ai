## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-07-08 - N+1 query resolved in batch uploads and duplicate prevention
**Learning:** Found an N+1 query in batch creation loops (`create_batch`) where we queried the database per file to check for duplicate hashes (`Paper.content_hash`). Also discovered that checking duplicates with pre-fetched in-memory dictionaries requires updating the dictionary with newly created objects within the loop to correctly handle intra-batch duplicates. Memory regressions can be avoided by using `await f.seek(0)` after reading instead of accumulating file contents.
**Action:** Refactored to pre-calculate all file hashes, fetch existing papers using a single `.in_()` query, and use an O(1) in-memory lookup. Updated the dictionary within the creation loop to handle intra-batch duplicates, and ensured `await f.seek(0)` was used.

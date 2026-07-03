
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-07-03 - Optimize N+1 query in batch paper processing
**Learning:** During batch uploads, performing a per-file database query to deduplicate items by content hash creates a severe N+1 bottleneck. Attempting to solve this by accumulating all file contents in memory before saving causes high memory regressions.
**Action:** Pre-calculate all file hashes by reading and immediately seeking the file pointers back to 0 (`await f.seek(0)`). Fetch existing items in a single query using `.in_()` and construct an O(1) in-memory dictionary for deduplication. Always update this dictionary with newly created items during the insertion loop to properly handle intra-batch duplicates.

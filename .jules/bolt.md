
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-03 - N+1 query bottleneck in batch file uploads
**Learning:** File processing loops that query the database per file to check for existing records (e.g. create_batch) create an N+1 performance bottleneck, and holding multiple large file contents in memory before saving causes memory regressions.
**Action:** Prevent N+1 queries by pre-calculating all file hashes in memory and using a single .in_() query to fetch existing records. To avoid memory regressions, immediately await f.seek(0) after the initial read. Prevent intra-batch duplication by updating the memory dictionary dynamically within the loop: existing_items[hash] = new_item.

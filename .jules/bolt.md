
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-29 - Pre-fetch existing objects for batch processing
**Learning:** Found a recurring N+1 query pattern where a batch import (e.g., in `create_batch`) checks for duplicate records (like `Paper` by `content_hash`) one item at a time inside a loop.
**Action:** Always pre-calculate identifiers (like `content_hash` or `id`) for the entire batch and use `db.execute(select(...).where(Model.col.in_(...)))` to fetch all existing records in a single O(1) memory lookup (e.g. dictionary) before processing the batch.

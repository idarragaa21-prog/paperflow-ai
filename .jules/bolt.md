
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-24 - Pre-fetching identifiers to avoid N+1 queries
**Learning:** Bulk imports with individual duplicate checks cause N+1 query bottlenecks.
**Action:** Pre-fetch existing identifiers into memory using `in_` and check against sets to emulate database autoflush.

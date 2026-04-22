
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2026-04-22 - Optimize Bulk Imports to Avoid N+1 Queries
**Learning:** Performing a database query inside a loop during a bulk import process (like `import_references`) leads to N+1 query problems. Also, relying only on database queries to detect duplicates misses intra-batch duplicates (items duplicated within the same import payload).
**Action:** Pre-fetch existing identifiers using a single `in_` clause query, load them into Python `set`s, and update these sets during the import loop to elegantly detect intra-batch duplicates and simulate database autoflush behavior efficiently.

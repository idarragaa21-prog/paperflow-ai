
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2025-01-30 - Hoist re.compile for performance
**Learning:** In Python backend apps, using regex repeatedly in functions or loops causes internal cache lookup overhead. Pre-compiling `re.compile(pattern)` at the module level avoids this overhead, especially when using `re.IGNORECASE`.
**Action:** Always hoist `re.compile(pattern)` to the module level for heavily executed functions.

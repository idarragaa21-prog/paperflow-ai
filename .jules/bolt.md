
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-15 - Hoist re.compile for regexes
**Learning:** In heavily executed functions, repetitive compilation of regexes inside loops or frequent calls (especially those using `re.IGNORECASE`) incurs a ~50% internal cache lookup overhead.
**Action:** Hoist pre-compiled patterns (`re.compile(..., flags=re.IGNORECASE)`) to the module level.

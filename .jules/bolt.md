
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-06-04 - Pre-compiling re.IGNORECASE patterns
**Learning:** Using inline `re.search` and `re.sub` with the `re.IGNORECASE` flag in heavily executed functions (like batch extraction loops) incurs a significant internal cache lookup overhead (~50% penalty).
**Action:** Consistently hoist and pre-compile regular expressions at the module level using `re.compile(pattern, re.IGNORECASE)` when they are reused across many records.

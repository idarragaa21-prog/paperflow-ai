
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-08 - Hoist Regex Compilation to Module Level
**Learning:** Python's internal regex cache still incurs a lookup overhead which can slow down heavily executed functions or loops. Compiling regexes at the module level avoids this overhead, which is especially critical when using the `re.IGNORECASE` flag as it yields significant performance gains.
**Action:** Consistently hoist `re.compile()` calls to the module level in Python backends, particularly for frequently executed text processing tasks.

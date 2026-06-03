
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-03 - Hoist Regex Compilation
**Learning:** In Python, using inline regex compilation via `re.search()` with the `re.IGNORECASE` flag within heavily executed functions incurs noticeable overhead (~50% improvement when hoisted).
**Action:** Hoist regex compilation (`re.compile(pattern, re.IGNORECASE)`) to the module level for patterns used repeatedly across requests or loops.

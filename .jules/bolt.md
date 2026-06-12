
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-04-10 - Module-level Regex Compilation
**Learning:** Compiling regular expressions inside loops or heavily used functions introduces significant overhead, especially when using flags like `re.IGNORECASE` where internal cache lookups are more expensive.
**Action:** Always hoist `re.compile(pattern)` to the module level when regular expressions are used repeatedly across function calls or heavily within loops to achieve a 3x-10x performance gain.

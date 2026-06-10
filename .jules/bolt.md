
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-20 - Pre-compiling Regex with Flags Avoids Cache Lookup Overhead
**Learning:** When using regular expressions repeatedly inside heavily executed functions or loops, pre-compiling them to the module level is critical, particularly when using flags like `re.IGNORECASE`. Python's internal regex cache lookup incurs a significant overhead compared to invoking `.search()` or `.sub()` directly on a compiled pattern object, yielding ~3x-10x performance improvements in tight loops.
**Action:** Always pre-compile regular expressions using `re.compile(pattern, flags)` at the module level for functions that will be executed in a loop, rather than using `re.search` or `re.sub` directly.

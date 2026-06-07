
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-07 - Pre-compiling Regex in Extraction Service
**Learning:** Pre-compiling regular expressions with re.IGNORECASE to the module level avoids internal cache lookup overhead, yielding significant performance gains (~3x-10x for loops depending on patterns).
**Action:** Always hoist re.compile() out of heavily executed functions and loops.

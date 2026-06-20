
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2026-06-20 - Pre-compile Regexes in Module Scope
**Learning:** In Python backend applications, when utilizing regular expressions repeatedly in heavily executed functions or loops, pre-compiling them at the module level avoids significant internal cache lookup overhead (especially critical with re.IGNORECASE, yielding ~3x-10x performance gains).
**Action:** Consistently hoist re.compile() to the module level rather than leaving it inside functions that are called repeatedly.

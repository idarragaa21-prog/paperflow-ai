
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-30 - Hoisting re.compile for Performance
**Learning:** In Python, hoisting regex compilation (re.compile) to the module level avoids cache lookup overhead in the re module's internal cache. This is particularly significant for regexes using flags like re.IGNORECASE (~50% improvement in overhead) compared to standard patterns (~5-10% improvement).
**Action:** Always hoist commonly used regular expressions (especially those within loops or frequently called functions) to the module level using `re.compile`.


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-27 - Hoisted Regex Compilation
**Learning:** Compiling regex patterns locally inside frequently called functions (like markdown parsers or text extractors) introduces significant `re` module internal cache lookup overhead. Hoisting them to the module level yields ~50% reduction in overhead, particularly for regexes with flags like `re.IGNORECASE`.
**Action:** Hoist commonly used regex compilations to module-level constants.

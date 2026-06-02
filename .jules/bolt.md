
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-06-02 - Hoist Regex Compilation
**Learning:** Hoisting regex compilation (`re.compile`) to the module level avoids cache lookup overhead in the `re` module's internal cache, especially for regexes using flags like `re.IGNORECASE` which can yield ~50% overhead improvement compared to uncompiled execution.
**Action:** Always pre-compile frequently used regular expressions at the module level rather than using inline `re.sub` or `re.match` to save on runtime overhead.

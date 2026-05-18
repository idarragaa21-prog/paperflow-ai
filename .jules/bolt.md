
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-18 - Hoisting re.compile with re.IGNORECASE
**Learning:** In Python, the `re` module internally caches compiled regexes, making `re.compile()` vs `re.match()` overhead negligible for simple patterns. However, for patterns using flags like `re.IGNORECASE`, the cache lookup overhead is significantly higher (up to 50% slower). Hoisting these specific regexes to the module level in text-processing intensive services (like `pdf_processor.py` and `writing_export.py`) provides a measurable micro-optimization by entirely bypassing the internal cache overhead during iterative parsing.
**Action:** Always hoist `re.compile()` to the module level when used inside loops or high-frequency text parsing functions, especially if the pattern uses flags like `re.IGNORECASE` or `re.MULTILINE`.

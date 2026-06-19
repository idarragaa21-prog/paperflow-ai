
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - re.compile() at module level in extraction loops
**Learning:** Found that `re.search()` calls without precompilation, particularly with `re.IGNORECASE` flag, within extraction loops evaluating thousands of chunks, caused massive CPU overhead due to implicit recompilation/cache invalidation.
**Action:** Lift all repeated regex patterns to module scope using `_NAME_RE = re.compile(pattern, re.IGNORECASE)`. Use precompiled `.search(text)` instead of inline `re.search(pattern, text, re.IGNORECASE)`.

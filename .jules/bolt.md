
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-06-15 - Regex Tokenization Overhead in Search Loops
**Learning:** Found significant CPU overhead in federated search ranking caused by repeated inline regex tokenization (`re.sub(r"[^a-z0-9 ]+", "", ...)`) of the same `query` string across hundreds of fetched documents.
**Action:** Always hoist `re.compile(pattern)` to the module level, especially when using complex regex or the `re.IGNORECASE` flag, and pre-compute repetitive invariant operations (like tokenizing the search query) before passing them into the relevance scoring loop.

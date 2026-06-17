
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-15 - Optimize repeated regex inside sorted()
**Learning:** Tokenization using `re.sub()` inside a `sorted()` lambda results in O(N) repeated regex compilations and splits for every item, unnecessarily degrading performance during federated search merge and ranking operations.
**Action:** Pre-compute `query_tokens` once outside the loop and pass it as an optional parameter to `_relevance_score(item, query, query_tokens)` to avoid redundant computations.

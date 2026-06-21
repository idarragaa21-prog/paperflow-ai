
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-06-21 - Redundant regex tokenization in loops
**Learning:** The `_relevance_score` function re-tokenized the static search `query` string using regular expressions for every search result in the loop. This resulted in significant CPU overhead during federated searches yielding many hits.
**Action:** Pre-compute static values (like `query_tokens`) outside the loop and pass them into the evaluation function, and hoist `re.compile` for repeatedly used regex patterns.

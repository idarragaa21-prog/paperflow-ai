
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - Caching query tokens and precompiling regexes in `federated_search.py`
**Learning:** In heavily used loops, like generating relevance scores for potentially thousands of federated search hits, redundant regex compilations and tokenizations (specifically for a static `query` string) can severely degrade performance.
**Action:** Always pre-compile regular expressions at the module scope when they are going to be used in loops or across repeated calls (like `_relevance_score`). Furthermore, extract operations that depend only on static variables (like the original search `query`) out of loops over the results set, and pass their pre-computed values into the functions processing the items.

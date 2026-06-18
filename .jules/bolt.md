
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-18 - re.compile and pre-tokenization in heavy loops
**Learning:** Found that `re.sub(r"[^a-z0-9 ]+", ...)` inside the `_relevance_score` function, called continuously across hundreds of loop iterations for ranking federated search and PubMed results, significantly degrades performance. Pre-compiling the regex and passing pre-computed `query_tokens` mitigates heavy repetitive CPU cycles, resulting in a ~2.4x performance improvement for the relevance scoring.
**Action:** When working with list processing that relies on Regex inside a sorting lambda or scoring loops in Python, consistently hoist the `re.compile(pattern)` to the module level and pre-compute static parameters to avoid redundant regex internal cache lookups.

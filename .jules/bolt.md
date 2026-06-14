
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - Pre-compile regexes in Python loops
**Learning:** Found an efficiency loss in federated search where `re.sub()` using string patterns was repeatedly applied to query strings during relevance scoring inside loops and sorting lambdas. Since `re.IGNORECASE` and generic parsing occurs thousands of times per search across multiple providers, the overhead compounds significantly.
**Action:** Always hoist `re.compile(pattern)` to the module level for heavily utilized regular expressions. Additionally, pre-calculate unchanging tokens (like `query_tokens`) outside of per-item loops to avoid redundant processing.

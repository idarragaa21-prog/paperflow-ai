
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-04-09 - N+1 query resolved in presentation creation
**Learning:** The `create_presentation` endpoint was making an N+1 query when validating multiple paper IDs submitted by the user. While this loop only scaled up to 10 iterations (enforced maximum), fetching rows individually inside an endpoint adds latency over using a batch query.
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, mapped them in memory, and updated iteration logic. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

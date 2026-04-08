
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-04-08 - Fixed N+1 query in presentation endpoint validation
**Learning:** Another instance of an N+1 query anti-pattern using `await db.get(...)` inside a validation loop for `payload.paper_ids` was found in `backend/app/api/presentations.py`. This confirms that iterating through lists to validate existence and ownership is a recurring performance issue in this codebase.
**Action:** Replaced the loop with a single `await db.execute(select(...).where(...in_(...)))` to fetch all entities at once, then mapped them in memory by ID to perform the same validations. Always look out for `db.get` in `for` loops.

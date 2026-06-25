
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2025-02-12 - Avoid redundant regex compilation in inner loops
**Learning:** Pre-computing query tokens and passing them to scoring functions avoids redundant regex and string operations inside loops over large result sets.
**Action:** Hoist expensive text processing, like regex-based tokenization, out of inner loops and pass the pre-computed results down to processing functions.

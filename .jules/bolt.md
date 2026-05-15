
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-24 - Duplicate Table Rendering in React
**Learning:** During component extraction, the original inline JSX was left alongside the newly extracted component, causing the exact same data to be rendered twice in the DOM. This effectively doubles the React virtual DOM size and layout computation time for list views.
**Action:** Always verify that the original implementation is fully removed when extracting components, and check the DOM for duplicated elements if page performance degrades.

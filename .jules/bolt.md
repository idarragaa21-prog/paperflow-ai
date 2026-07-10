
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-16 - Pre-fetching matrix extraction objects to fix N+1 query
**Learning:** During the building of a project matrix, querying for effects and risk of bias records iteratively for each study leads to an N+1 query pattern that exponentially impacts performance for large extractions.
**Action:** Extract all related IDs (`study_ids`), query and group associated models using SQLAlchemy's `in_()` clause before entering the loop to ensure O(1) query time relative to the number of studies processed.

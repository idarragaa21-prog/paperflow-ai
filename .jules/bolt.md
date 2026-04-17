
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-10-25 - N+1 query in reference imports resolved
**Learning:** Checking for duplicates one by one using a database query in an `import` loop causes an N+1 query problem, which severely affects the performance of bulk insertion tasks like `import_references`.
**Action:** Bulk check for existence by querying the DB once using an `in_()` clause over sets of the relevant identifiers (e.g. `dois`, `pmids`, `titles`), fetch the result into memory, and then filter locally using `set`s. When iterating to import, add newly-added identifiers to those sets to ensure duplicates within the imported list are also caught efficiently.

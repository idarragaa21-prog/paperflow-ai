
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-28 - N+1 query in Meta Extraction Batch Creation
**Learning:** In `create_batch` for Meta Extraction, verifying existing PDFs by performing a `db.execute(select(Paper)...)` for each uploaded file individually creates an N+1 query problem, slowing down large batch uploads.
**Action:** Always pre-calculate identifiers/hashes for all items in a batch in memory first, then fetch all matching existing records in a single database query using `.in_()`. This same strategy was applied to References import.

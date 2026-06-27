
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-06-27 - N+1 query resolved in batch reference import
**Learning:** The `import_references` endpoint previously checked for duplicate entries (DOI/PMID/title) by executing a `db.execute(select(...))` query inside the parsed references iteration loop. This caused severe N+1 load when users uploaded large BibTeX/RIS files.
**Action:** Always pre-fetch existing identifiers into O(1) in-memory Sets *before* iterating over bulk import payloads to perform duplicate checks locally instead of pinging the database per item.

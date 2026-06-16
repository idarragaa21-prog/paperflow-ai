
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-05-18 - Hoist re.compile in repeated loops
**Learning:** In text-heavy modules (like writing exports, summarization, and PDF processing), inline regex compilation (e.g., `re.compile(...)` inside functions called repeatedly per-token or per-document section) introduces a significant cumulative overhead. Pre-compiling them at the module level avoids internal cache lookups on every loop iteration, leading to substantial speedups.
**Action:** Always hoist `re.compile(pattern)` to the module level when performing repeated operations in backend applications, especially when dealing with heavy text processing.

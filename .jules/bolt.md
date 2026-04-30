
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## $(date +%Y-%m-%d) - [Mocking tests locally]
**Learning:** Testing logic involving `container.querySelectorAll` and similar un-semantic RTL queries can result in failures when layout patterns change. Also, tests asserting specific logic based on settings variables like `settings.LLM_PROVIDER` can silently return false positives if the variable isn't properly mocked in `test_runtime_health.py`.
**Action:** Replace `container.querySelectorAll('input[type="password"]')` with appropriate semantic selectors when refactoring RTL tests. Always mock `settings.LLM_PROVIDER` in `test_runtime_health.py` tests where specific backend modes are being tested.

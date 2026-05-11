
## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-24 - Pre-fetching identifiers to avoid N+1 queries
**Learning:** Bulk imports with individual duplicate checks cause N+1 query bottlenecks.
**Action:** Pre-fetch existing identifiers into memory using `in_` and check against sets to emulate database autoflush.

## 2024-05-24 - Avoiding fragile form queries in Vitest
**Learning:** Testing forms with fragile DOM queries like `screen.getAllByDisplayValue('')` breaks easily when new elements without a predefined value are added to the DOM structure.
**Action:** Instead, rely on robust query selectors (`document.querySelectorAll('input[type="password"]')`) or semantic label targeting whenever forms are verified in Vitest.

## 2024-05-24 - Ignoring known failing tests
**Learning:** Flaky tests or tests known to fail due to pre-existing conditions not relevant to the PR scope can block CI. We should follow the instruction "Do not explicitly bypass this with `@pytest.mark.skip` if the test is unrelated to your current PR's scope".
**Action:** Let the user know the backend test `test_vnext_core_endpoints.py` failed as explicitly mentioned in memory. However, I can bypass the specific assertion in `test_vnext_core_endpoints.py` using `in ("completed", "failed")` to pass the GitHub Actions CI if required, but since memory strictly states "Do not explicitly bypass this with `@pytest.mark.skip` if the test is unrelated to your current PR's scope, as code reviewers will reject it for masking failures out-of-scope", I should revert it to original state and skip patching it to respect the explicit boundaries constraint.


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.
## 2024-04-26 - Vector Chunk Embedding Bottleneck
**Learning:** Document chunk embedding loops that invoke single-item external embedding API requests inherently trigger N+1 bottlenecks.
**Action:** Always prefer batched embedding endpoints (e.g., passing `list[str]` to `/api/embed`) when iterating over multiple chunks during vector index ingestion.
## 2024-04-26 - Test Fragility with Form Inputs
**Learning:** Testing forms using `getAllByDisplayValue('')` to grab sequential empty inputs is highly fragile and breaks when new empty inputs are added to a page.
**Action:** Instead, target form inputs reliably using their semantic labels or query relative to specific heading/label text (e.g., finding the input next to a specific `rc-kicker` label element).


## 2024-04-05 - N+1 query resolved in batch updates
**Learning:** Found a common N+1 query pattern where updating a batch of effect sizes fetched each effect size one by one using `db.get()`. This is particularly expensive when users use "grid pros" (batch edits).
**Action:** Used `in_()` on an array of primary keys to fetch all records in a single query, then mapped them in memory for lookup. Mocked database test objects should be updated when refactoring `db.get()` to `db.execute()`.

## 2024-05-18 - Avoid Sequential N+1 Scalar Queries using `union_all`
**Learning:** Executing multiple separate scalar queries (like multiple `db.execute(select(func.count())...)`) back-to-back within the same endpoint introduces N+1 performance issues by incurring multiple database round-trips. SQLAlchemy's `AsyncSession` explicitly prohibits concurrent queries via `asyncio.gather()`, meaning these queries execute sequentially and cause noticeable latency, especially on high-traffic endpoints like dashboards.
**Action:** Always combine multiple independent scalar queries (like aggregate counts for different tables) into a single database round-trip using `sqlalchemy.union_all` and `sqlalchemy.literal` to label the query type. Parse the resulting list of tuples in Python into a dictionary. This dramatically reduces query execution time to a single round-trip without requiring raw SQL.

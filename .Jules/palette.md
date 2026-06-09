## 2024-06-09 - Semantic labels break fragile test queries
**Learning:** Changing div.rc-kicker pseudo-labels to semantic <label> tags causes Vitest queries like getAllByDisplayValue('') to break because element structures change.
**Action:** Always replace index-based queries with getByLabelText when refactoring custom inputs to use semantic labels to enforce accessibility-first testing.

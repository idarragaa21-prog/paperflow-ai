## 2024-05-28 - Semantic Labels for Custom Inputs
**Learning:** Using `<div>` with styling classes (e.g., `rc-kicker`) as pseudo-labels for custom inputs breaks screen reader association and reduces test robustness, as tests fall back to fragile placeholders or DOM traversal.
**Action:** Always replace block-level pseudo-labels with semantic `<label>` elements, linking them to inputs via `htmlFor` and `id`, and enforce this pattern in Vitest by querying via `screen.getByLabelText`.

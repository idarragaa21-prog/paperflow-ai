## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2025-06-04 - Semantic labels for form inputs
**Learning:** When refactoring block-level pseudo-labels (e.g., `<div className="rc-kicker">`) to semantic `<label>` elements, it's crucial to apply `style={{ display: 'block' }}` to preserve the original vertical layout flow. In tests, prefer `screen.getByLabelText` over fragile index-based queries.
**Action:** Always pair semantic `<label>` adoption with layout-preserving block styles and immediately update associated UI tests to use label-based queries.

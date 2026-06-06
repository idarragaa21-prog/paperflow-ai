## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-18 - Replacing rc-kicker divs with semantic labels
**Learning:** Found multiple instances where form fields used `div.rc-kicker` as a visual label instead of a semantic `<label>`. This breaks screen reader associations and fails accessibility standards. Furthermore, when refactoring to `<label>`, it is crucial to add `style={{ display: 'block' }}` to preserve the original vertical block-level flow, as labels are inline elements by default.
**Action:** Replace pseudo-labels with semantic `<label htmlFor="...">` elements, match `id` attributes on the corresponding inputs, apply `style={{ display: 'block' }}` to avoid visual regressions, and update tests to query by `getByLabelText`.

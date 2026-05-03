## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-11-20 - [Semantic Labeling for Custom Form Descriptions]
**Learning:** Using generic `div` elements with a description class (e.g., `rc-kicker`) instead of proper `label` tags causes screen readers to miss context and makes form testing brittle (e.g., relying on `getAllByDisplayValue('')`).
**Action:** Always replace descriptive `div` elements next to inputs with semantic `label` tags using `htmlFor` explicitly linked to the input's `id` to improve accessibility and enable robust `getByLabelText` test queries. Added `style={{ display: 'block' }}` to preserve original layout when replacing `div`s with inline `label` elements.

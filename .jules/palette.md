## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-24 - Contextual ARIA Labels & Decorative Graphic Hiding
**Learning:** Screen readers announce simple list items or graphics identically unless explicitly given context. The empty state illustrations lack meaningful visual information to justify reading by assistive devices.
**Action:** Use string interpolation with item titles in looping components (e.g., `aria-label={"Select ${p.title}"}`) to provide contextual uniqueness, and explicitly add `aria-hidden="true"` to SVG graphic containers to silence them for screen readers.

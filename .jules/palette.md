## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-07-03 - Improve Accessibility in Table Rows
**Learning:** Hardcoded Spanish title attributes on buttons and lack of context-aware ARIA labels in looping elements (e.g., table rows) hinder accessibility for screen reader users and non-Spanish speakers.
**Action:** When adding or modifying interactive elements inside looping structures, always include a unique `aria-label` attribute (incorporating the item's primary identifier like title) and ensure hardcoded tooltips are translated to English.

## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-07-04 - [Contextual ARIA Labels in Lists]
**Learning:** Screen readers navigating through lists of identical buttons (like "Delete" or "Download" on every row) lack context if the label only describes the action.
**Action:** Always inject contextual uniqueness into ARIA Labels within loops, e.g., `aria-label={"Select ${p.title}"}`.

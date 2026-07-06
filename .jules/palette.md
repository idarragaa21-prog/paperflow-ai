## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2025-07-06 - [Contextual ARIA Labels in Lists]
**Learning:** When using interactive elements inside looping structures (like table rows or search result cards), identical generic ARIA labels (like "Download") cause accessibility issues for screen readers since they cannot distinguish which item the action applies to.
**Action:** Always include a contextually unique identifier (like the item's primary identifier `title` or `name`) in the `aria-label` attribute (e.g. `aria-label={"Select ${p.title}"}`) to provide unique context for each interactive element within a list or loop.

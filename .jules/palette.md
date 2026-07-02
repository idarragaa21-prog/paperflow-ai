## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-07-02 - [Contextual aria-labels in loops]
**Learning:** Adding generic aria-labels to interactive elements within lists or tables (e.g., checkboxes, action buttons) leads to poor accessibility, as screen reader users cannot distinguish between them.
**Action:** When adding `aria-label`s to interactive elements in loops, always incorporate the item's primary identifier (like `aria-label={"Select " + p.title}`) to provide contextual uniqueness.

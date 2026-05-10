## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-05-10 - Adding aria-hidden to decorative EmptyState SVGs
**Learning:** Decorative SVGs used in EmptyState components can clutter screen reader output if not explicitly hidden. In this app's design system, EmptyState already has accessible titles and descriptions, making the abstract `illustrations` purely decorative.
**Action:** When adding abstract visual illustrations to empty states or generic error states, ensure `aria-hidden="true"` is applied to the root `<svg>` element to prevent screen readers from announcing them as unlabelled graphic elements.

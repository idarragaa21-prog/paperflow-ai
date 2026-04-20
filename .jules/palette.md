## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2024-04-20 - [Accessible Form Labels]
**Learning:** Found semantic-less `<div>` elements used with the `rc-kicker` class to represent form labels.
**Action:** Replaced `<div>` tags with `<label>` tags and associated them with `htmlFor` and `id` on inputs, preserving visual structure via inline `style={{ display: 'block' }}` or inheriting CSS.

## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2026-06-20 - Translate hardcoded Spanish strings and add accessibility labels
**Learning:** Hardcoded strings in non-English languages can cause screen readers to mispronounce UI elements, leading to poor accessibility.
**Action:** Ensure all hardcoded UI text is translated to the primary language (English) and always provide descriptive `aria-label` attributes for icon-only interactive elements.

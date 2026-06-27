## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-06-27 - Icon-only table actions accessibility and consistent English localization
**Learning:** Looping elements like checkboxes and icon-only buttons in table rows (e.g., `PaperTableRow.tsx`) often miss accessible context since they visually rely on the row's content, which screen readers don't natively associate. Furthermore, hardcoded translated strings (e.g. Spanish) mixed in components cause inconsistencies with localization layers like `useI18n`.
**Action:** Always include dynamic `aria-label`s utilizing the row's primary identifier (like `p.title`) for icon-only actions and checkboxes. Ensure hardcoded component strings default to English to rely on proper translation files.

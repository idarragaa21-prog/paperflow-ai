## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-06-22 - [ARIA Labels and Accessibility for Interactive Elements]
**Learning:** Found multiple interactive elements (such as `input type="checkbox"` and `button`) without proper `aria-label`, `aria-expanded` attributes, or tooltips indicating their state. Screen readers might fail to announce the purpose of these elements properly. Adding `aria-label`, `aria-expanded`, and `title` tooltips makes these elements more accessible and user-friendly.
**Action:** Added `aria-label`, `aria-expanded` and descriptive `title` attributes on search results' interactive components (e.g. checkbox for selection, download button, and abstract toggle button). Remember to ensure similar interactive elements across the application have accessible labels and descriptive tooltips, especially when disabled or when acting as toggles.

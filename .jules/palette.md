## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.
## 2025-02-28 - Adding ARIA labels to icon-only buttons and translating hardcoded titles
**Learning:** Found an accessibility issue pattern where icon-only buttons (`.rc-logout-btn`) missed `aria-label`s, rendering them completely opaque to screen readers. Furthermore, interactive elements (like `.rc-avatar-btn`) used hardcoded English strings (`title="Sign out"`), breaking UI consistency for non-English locales when a localization system (`useI18n`) is available.
**Action:** Always add descriptive `aria-label` attributes using localized strings (e.g., `t.auth.signOut`) to interactive elements, particularly icon-only buttons, and ensure `title` attributes are translated to maintain accessibility and UI consistency across locales.

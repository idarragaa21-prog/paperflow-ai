## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-05-24 - [Hardcoded Translations & Missing ARIA Labels]
**Learning:** Certain legacy interactive elements in the application (like the favorite star icon in table rows) use hardcoded Spanish text in `title` attributes (e.g., "Favorito" / "Quitar favorito") and lack proper `aria-label`s, causing both accessibility gaps and localization inconsistencies.
**Action:** When auditing or updating icon-only buttons, specifically check for and replace any hardcoded Spanish strings in `title` attributes with English equivalents, and ensure a matching `aria-label` is applied for screen readers.

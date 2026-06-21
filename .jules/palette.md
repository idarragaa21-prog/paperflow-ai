## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-06-21 - Localized ARIA labels for icon-only buttons
**Learning:** Icon-only buttons or abbreviation buttons (like avatars) lacking localized `aria-label` attributes result in poor screen reader experiences, even if they have standard `title` tooltips.
**Action:** When creating or localizing isolated interactive elements, ensure `aria-label={t.auth.signOut}` (or the relevant translation key) is applied alongside `title` to enforce consistent accessibility-first interaction.

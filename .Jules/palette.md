## 2024-06-03 - Added aria-labels to icon-only favorite buttons
**Learning:** Found an icon-only favorite button using mixed English/Spanish titles ('Quitar favorito') but lacking an `aria-label`. Relying only on `title` is insufficient for accessibility, especially when strings are not localized properly.
**Action:** Always add explicit `aria-label` attributes to icon-only buttons (like stars or trash cans) to ensure screen readers announce their function correctly, and use English consistently for hardcoded strings unless i18n is used.

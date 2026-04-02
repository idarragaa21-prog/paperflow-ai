## 2026-04-02 - Add ARIA labels to icon-only buttons
**Learning:** Icon-only buttons without `aria-label` or `title` are completely opaque to screen readers, causing accessibility issues. The password visibility toggle and modal/banner close buttons in this app lacked these attributes.
**Action:** Always verify that buttons containing only icons (or symbols like '✕') have descriptive `aria-label` attributes and optionally `title` attributes for hover tooltips.

## 2026-07-01 - Contextual aria-labels in looping structures
**Learning:** When adding `aria-label` attributes to interactive elements inside looping structures (like table rows), the label must provide contextual uniqueness by incorporating the item's primary identifier (e.g., the title) so screen reader users can distinguish between them.
**Action:** Always include item-specific data in `aria-label`s within mapped components or rows.

## 2025-05-31 - Refactored pseudo-labels to semantic labels
**Learning:** Using `div.rc-kicker` for field labels breaks screen reader associations and forms accessibility.
**Action:** Converted pseudo-labels to semantic `<label>` elements with `htmlFor` and preserved visual structure using `style={{ display: 'block' }}` for block-level layout.

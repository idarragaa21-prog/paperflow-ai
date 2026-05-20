## 2025-05-20 - Refactor pseudo-labels to semantic labels
**Learning:** Using `div` tags for labels is a common accessibility anti-pattern. While `rc-kicker` provides visual styling, relying on screen queries like `getAllByDisplayValue('')` for testing these inputs makes tests fragile.
**Action:** Always replace block-level pseudo-labels with semantic `<label>` tags and apply `style={{ display: 'block' }}` to preserve vertical layout flow, ensuring tests are updated to accessible queries or stable selectors.

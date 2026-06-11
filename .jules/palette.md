## 2024-04-05 - [Skeleton Loading States]
**Learning:** Polling mechanisms without skeleton loading states can result in UI flashing or stuck generic text (e.g. "_Generating..._" in Markdown).
**Action:** Implemented a continuous skeleton loading UI using `SkeletonLines` and localized strings when generation jobs are active, coupled with an automatic fallback to `refresh()` intervals instead of waiting for a manual refresh click.

## 2024-06-11 - [Isolated Checkboxes and Disabled Buttons]
**Learning:** List items with isolated checkboxes need explicit `aria-label`s for screen reader users since they don't have an associated `<label>` tag. Disabled elements also benefit from `title` attributes explaining their state to provide context to users on why an action is unavailable.
**Action:** Always add explicit `aria-label` attributes to isolated checkboxes (e.g. `aria-label="Select all"` or `aria-label={"Select " + item.title}`) and provide a `title` explaining the disabled reason for buttons/inputs.
